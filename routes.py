from fastapi import APIRouter, Depends, HTTPException, Security
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import TodoCreate, TodoRead, TodoUpdate
from auth import (
    get_current_user,
    create_access_token,
    get_password_hash,
    verify_password,
    generate_raw_refresh_token,
    hash_refresh_token,
    REFRESH_EXPIRE_DAYS,
)
from crud import (
    get_todo_by_id,
    list_todos,
    create_todo as crud_create_todo,
    get_user_by_email,
    create_user as crud_create_user,
)
from crud import (
    create_refresh_token as crud_create_refresh_token,
    get_refresh_token_by_hash as crud_get_refresh_token_by_hash,
    revoke_refresh_token as crud_revoke_refresh_token,
    list_refresh_tokens_for_user as crud_list_refresh_tokens_for_user,
    revoke_all_refresh_tokens_for_user as crud_revoke_all_refresh_tokens_for_user,
)
from db import get_db
from models import Todo, User

# using JSON-only auth now; no form-based OAuth2PasswordRequestForm
from fastapi import Request
from datetime import datetime, timezone, timedelta
from schemas import RefreshRequest, TokenResponse, LoginRequest

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def login_json(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Аутентификация: возвращает access и refresh токены."""
    user = await get_user_by_email(db, payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token(user.email, user.scopes or [])
    raw_refresh = generate_raw_refresh_token()
    token_hash = hash_refresh_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    from models import RefreshToken

    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    await crud_create_refresh_token(db, rt)
    return {"access_token": token, "token_type": "bearer", "refresh_token": raw_refresh}


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Обновить access token по refresh token."""
    raw = payload.refresh_token
    if not raw:
        raise HTTPException(status_code=400, detail="refresh_token required")
    token_hash = hash_refresh_token(raw)
    rt = await crud_get_refresh_token_by_hash(db, token_hash)
    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")
    # Rotation: создаём новый refresh token, помечаем старый revoked и связываем
    new_raw = generate_raw_refresh_token()
    new_hash = hash_refresh_token(new_raw)
    new_expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    from models import RefreshToken

    new_rt = RefreshToken(
        user_id=rt.user_id,
        token_hash=new_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=new_expires,
    )
    await crud_create_refresh_token(db, new_rt)
    # revoke old
    rt.revoked = True
    rt.replaced_by_id = new_rt.id
    rt.last_used_at = datetime.now(timezone.utc)
    db.add(rt)
    await db.commit()
    # issue new access
    # Получаем пользователя по id и генерируем новый access
    from crud import get_user_by_id

    user_obj = await get_user_by_id(db, rt.user_id)
    if not user_obj:
        raise HTTPException(status_code=400, detail="User not found")
    access = create_access_token(user_obj.email, user_obj.scopes or [])
    return {"access_token": access, "token_type": "bearer", "refresh_token": new_raw}


@router.post("/token/revoke")
async def revoke_refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Отозвать refresh token или все сессии пользователя."""
    body = await request.json()
    raw = body.get("refresh_token")
    if raw:
        token_hash = hash_refresh_token(raw)
        rt = await crud_get_refresh_token_by_hash(db, token_hash)
        if not rt:
            raise HTTPException(status_code=404, detail="Not found")
        if rt.user_id != int(current_user["id"]) and "admin" not in (
            current_user.get("scopes") or []
        ):
            raise HTTPException(status_code=403, detail="Not authorized")
        await crud_revoke_refresh_token(db, rt)
        return {"ok": True}
    # если не указан refresh_token — ревок всех токенов текущего пользователя
    await crud_revoke_all_refresh_tokens_for_user(db, int(current_user["id"]))
    return {"ok": True}


@router.get("/sessions")
async def list_sessions(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Список refresh-сессий (admin видит все)."""
    if "admin" in (current_user.get("scopes") or []):
        # показать все сессии
        q = await db.execute(
            "select id, user_id, issued_at, expires_at, revoked, device_id from refresh_tokens"
        )
        return [
            dict(
                id=r[0],
                user_id=r[1],
                issued_at=r[2].isoformat() if r[2] else None,
                expires_at=r[3].isoformat() if r[3] else None,
                revoked=bool(r[4]),
                device_id=r[5],
            )
            for r in q.fetchall()
        ]
    sessions = await crud_list_refresh_tokens_for_user(db, int(current_user["id"]))
    return [
        {
            "id": s.id,
            "issued_at": s.issued_at.isoformat() if s.issued_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "revoked": s.revoked,
            "device_id": s.device_id,
        }
        for s in sessions
    ]


@router.post("/register")
async def register(
    email: str,
    password: str,
    scopes: List[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Security(get_current_user, scopes=["admin"]),
):
    """Создать пользователя (admin only)."""
    # базовая политика паролей (можно расширить при необходимости)
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password too short (min 8 chars)")

    if await get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = get_password_hash(password)
    user = User(email=email, hashed_password=hashed, scopes=scopes or ["user"])
    created = await crud_create_user(db, user)
    return {"email": created.email, "scopes": created.scopes}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    """Информация о текущем пользователе."""
    return current_user


@router.get("/admin")
def admin_only(current_user=Security(get_current_user, scopes=["admin"])):
    """Эндпоинт только для админов."""
    return {"ok": True, "msg": f"Welcome, {current_user['email']}!"}


@router.post("/todos", response_model=TodoRead)
async def create_todo(
    payload: TodoCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать задачу для текущего пользователя."""
    # owner_id — берем из id аутентифицированного пользователя
    todo = Todo(
        title=payload.title,
        description=payload.description,
        owner_id=int(current_user["id"]),
    )
    return await crud_create_todo(db, todo)


@router.get("/todos", response_model=List[TodoRead])
async def list_todos_route(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Список задач (admin видит все, user — свои)."""
    if "admin" in (current_user.get("scopes") or []):
        return await list_todos(db)
    return await list_todos(db, owner_id=int(current_user["id"]))


@router.get("/todos/{todo_id}", response_model=TodoRead)
async def get_todo(
    todo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить задачу по id (владелец или admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (
        current_user.get("scopes") or []
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view this todo")
    return todo


@router.patch("/todos/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить задачу (владелец или admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (
        current_user.get("scopes") or []
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this todo"
        )
    if payload.title is not None:
        todo.title = payload.title
    if payload.description is not None:
        todo.description = payload.description
    if payload.is_done is not None:
        todo.is_done = payload.is_done
    from datetime import datetime, timezone

    todo.updated_at = datetime.now(timezone.utc)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить задачу (владелец или admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (
        current_user.get("scopes") or []
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this todo"
        )
    await db.delete(todo)
    await db.commit()
    return {"ok": True}
