from fastapi import APIRouter, Depends, HTTPException, Security, Response
from typing import List, Optional
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
    pwd_context,
)
from passlib.exc import UnknownHashError
from crud import (
    get_todo_by_id,
    create_todo as crud_create_todo,
    get_user_by_email,
    create_user as crud_create_user,
)
from crud import get_user_by_id
from crud import (
    create_refresh_token as crud_create_refresh_token,
    get_refresh_token_by_hash as crud_get_refresh_token_by_hash,
    revoke_refresh_token as crud_revoke_refresh_token,
    list_refresh_tokens_for_user as crud_list_refresh_tokens_for_user,
    revoke_all_refresh_tokens_for_user as crud_revoke_all_refresh_tokens_for_user,
    revoke_refresh_tokens_for_user_device_type as crud_revoke_refresh_tokens_for_user_device_type,
)
from db import get_db
from sqlalchemy import text, select, asc, desc
from models import Todo, User, RefreshToken

from fastapi import Request
from datetime import datetime, timezone, timedelta
from schemas import RefreshRequest, TokenResponse, LoginRequest, DeviceType, UserCreate, UserRead, PasswordChange, PasswordResetRequest
# ...existing code...


# Split endpoints into multiple routers so OpenAPI groups appear with meaningful tags
# This keeps existing paths intact but organizes docs: Auth, Users, Todos, Sessions
auth_router = APIRouter(tags=["Auth"])
users_router = APIRouter(tags=["Users"])
todos_router = APIRouter(tags=["Todos"])
sessions_router = APIRouter(tags=["Sessions"])
admin_router = APIRouter(tags=["Admin"])

# Combined router exported to main.py (keeps main.py include_router call working)
router = APIRouter()


@auth_router.post("/token", response_model=TokenResponse)
async def login_json(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Аутентификация: возвращает access и refresh токены."""
    user = await get_user_by_email(db, payload.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    try:
        ok = verify_password(payload.password, user.hashed_password)
    except UnknownHashError:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    # Если хэш устарел (needs_update) — обновим на argon2
    try:
        if pwd_context.needs_update(user.hashed_password):
            user.hashed_password = get_password_hash(payload.password)
            db.add(user)
            await db.commit()
            await db.refresh(user)
    except Exception:
        # Не критично: если апдейт не прошёл — продолжаем работу (аутентификация успешна)
        pass
    token = create_access_token(user.email, user.scopes or [])
    raw_refresh = generate_raw_refresh_token()
    token_hash = hash_refresh_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    # validate/normalize device_type
    device_type = None
    if payload.device_type:
        try:
            device_type = DeviceType(payload.device_type.lower()).value
        except Exception:
            raise HTTPException(status_code=400, detail="device_type must be 'web' or 'mobile'")
        await crud_revoke_refresh_tokens_for_user_device_type(db, user.id, device_type)
    # capture device_id (from payload) and client metadata
    device_id = payload.device_id
    user_agent = request.headers.get("user-agent")
    xff = request.headers.get("x-forwarded-for")
    ip_addr = None
    if xff:
        ip_addr = xff.split(",")[0].strip()
    else:
        ip_addr = request.client.host if request.client else None
    from models import RefreshToken

    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        device_type=device_type,
        device_id=device_id,
        user_agent=user_agent,
        ip_address=ip_addr,
    )
    await crud_create_refresh_token(db, rt)
    return {"access_token": token, "token_type": "bearer", "refresh_token": raw_refresh}


@auth_router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Обновить access token по refresh token."""
    raw = payload.refresh_token
    if not raw:
        raise HTTPException(status_code=400, detail="refresh_token required")
    token_hash = hash_refresh_token(raw)
    rt = await crud_get_refresh_token_by_hash(db, token_hash)
    if not rt or rt.revoked:
        # If token revoked and replaced_by_id present, it's likely reuse (theft). Keep current behavior
        # and return Invalid. Clients should replace their stored token after successful refresh.
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Normalize expires_at to timezone-aware (DB may contain naive timestamps)
    expires_at = rt.expires_at
    if expires_at is None:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    if expires_at.tzinfo is None:
        # assume UTC for legacy/naive values
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")
    # Rotation: создаём новый refresh token, помечаем старый revoked и связываем
    new_raw = generate_raw_refresh_token()
    new_hash = hash_refresh_token(new_raw)
    new_expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    from models import RefreshToken

    # Use device metadata from the stored refresh token. The client does not
    # need to (and should not) re-send device_type/device_id when refreshing.
    device_type = rt.device_type
    # Revoke other active tokens for this device_type (enforce single active per device_type)
    if device_type:
        await crud_revoke_refresh_tokens_for_user_device_type(db, rt.user_id, device_type)
    # reuse stored device_id
    device_id = rt.device_id
    user_agent = request.headers.get("user-agent")
    xff = request.headers.get("x-forwarded-for")
    ip_addr = None
    if xff:
        ip_addr = xff.split(",")[0].strip()
    else:
        ip_addr = request.client.host if request.client else None

    new_rt = RefreshToken(
        user_id=rt.user_id,
        token_hash=new_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=new_expires,
        device_type=device_type,
        device_id=device_id,
        user_agent=user_agent,
        ip_address=ip_addr,
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


@auth_router.post("/token/revoke")
async def revoke_refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Отозвать refresh token или все сессии пользователя."""
    # request.json() raises JSONDecodeError if body is empty or not JSON.
    # Accept empty body to mean "revoke all sessions for current user".
    try:
        body = await request.json()
        if body is None:
            body = {}
    except Exception:
        # Could be JSONDecodeError or other issues reading body -> treat as empty
        body = {}
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


@sessions_router.get("/sessions")
async def list_sessions(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Список refresh-сессий (admin видит все)."""
    if "admin" in (current_user.get("scopes") or []):
        # показать все сессии
        q = await db.execute(
            text("select id, user_id, issued_at, expires_at, revoked, device_id from refresh_tokens")
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


@sessions_router.delete("/sessions/{session_id}")
async def revoke_session_by_id(
    session_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a single refresh session by its id (owner or admin)."""
    from models import RefreshToken
    q = await db.execute(select(RefreshToken).where(RefreshToken.id == session_id))
    rt = q.scalars().first()
    if not rt:
        raise HTTPException(status_code=404, detail="Session not found")
    if rt.user_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="Not authorized to revoke this session")
    from datetime import datetime, timezone

    # Soft-revoke: mark revoked and update last_used_at (existing behavior)
    rt.revoked = True
    rt.last_used_at = datetime.now(timezone.utc)
    db.add(rt)
    await db.commit()
    return {"ok": True, "revoked": True}


@users_router.post("/register", response_model=UserRead, status_code=201)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """Создать пользователя (admin only). Принимает JSON body: UserCreate."""
    # базовая политика паролей (можно расширить при необходимости)
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short (min 8 chars)")

    existing = await get_user_by_email(db, payload.email)
    if existing:
        # Safer idempotency: only return the existing user if the caller
        # supplies the same password. If the password doesn't match, we
        # treat this as a conflict to avoid silently accepting different
        # credentials for an already-registered email (prevents confusion
        # and potential accidental account takeover attempts).
        try:
            pw_ok = verify_password(payload.password, existing.hashed_password)
        except UnknownHashError:
            pw_ok = False
        if pw_ok:
            # Returning existing resource — set status 200 instead of 201
            if response is not None:
                response.status_code = 200
            return existing
        # Password mismatch — signal that the resource already exists
        raise HTTPException(status_code=409, detail="User with this email already exists")

    hashed = get_password_hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed, scopes=payload.scopes or ["user"])
    created = await crud_create_user(db, user)
    return created



@users_router.post("/change-password")
async def change_password(
    payload: PasswordChange,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password (requires current password)."""
    user = await get_user_by_id(db, int(current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        ok = verify_password(payload.current_password, user.hashed_password)
    except UnknownHashError:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="Current password incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password too short (min 8 chars)")
    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    await db.commit()
    return {"ok": True}



@users_router.post("/password-reset-request")
async def password_reset_request(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Stub: request a password reset. In production this would enqueue an email with a signed token."""
    user = await get_user_by_email(db, payload.email)
    if not user:
        # Don't leak existence
        return {"ok": True}
    # TODO: generate signed reset token and send via email
    return {"ok": True}


@admin_router.get("/admin/stats")
async def admin_stats(current_user=Security(get_current_user, scopes=["admin"]), db: AsyncSession = Depends(get_db)):
    """Simple admin stats: counts of users, todos, active sessions."""
    q = await db.execute(text("select count(*) from users"))
    users_count = q.scalar() or 0
    q = await db.execute(text("select count(*) from todos"))
    todos_count = q.scalar() or 0
    q = await db.execute(text("select count(*) from refresh_tokens where revoked = false"))
    sessions_count = q.scalar() or 0
    return {"users": users_count, "todos": todos_count, "active_sessions": sessions_count}



@admin_router.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@admin_router.get("/metrics")
async def metrics():
    """Metrics stub — integrate Prometheus or another exporter in production."""
    return {"metrics": {}}


@admin_router.post("/admin/cleanup_sessions")
async def cleanup_sessions(current_user=Security(get_current_user, scopes=["admin"]), db: AsyncSession = Depends(get_db)):
    """Cleanup expired or long-revoked refresh tokens. Returns number of revoked rows updated."""
    # Simple implementation: mark tokens with expires_at < now or revoked True as revoked (idempotent)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    # Only select tokens that are expired and not yet revoked
    q = await db.execute(select(RefreshToken).where((RefreshToken.expires_at < now) & (RefreshToken.revoked.is_(False))))
    tokens = q.scalars().all()
    count = 0
    for t in tokens:
        t.revoked = True
        t.last_used_at = now
        db.add(t)
        count += 1
    await db.commit()
    return {"revoked_marked": count}


@users_router.get("/me")
def me(current_user=Depends(get_current_user)):
    """Информация о текущем пользователе."""
    return current_user


@users_router.get("/admin")
def admin_only(current_user=Security(get_current_user, scopes=["admin"])):
    """Эндпоинт только для админов."""
    return {"ok": True, "msg": f"Welcome, {current_user['email']}!"}


@todos_router.post("/todos", response_model=TodoRead)
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


@todos_router.get("/todos", response_model=List[TodoRead])
async def list_todos_route(
    skip: int = 0,
    limit: int = 50,
    owner_id: Optional[int] = None,
    is_done: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_desc: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List todos with filters, pagination and simple sorting.

    Admins may pass owner_id to list others' todos. Regular users will only
    see their own todos regardless of owner_id param.
    """
    # enforce ownership for non-admins
    if "admin" not in (current_user.get("scopes") or []):
        owner_id = int(current_user["id"])

    # Basic selection using ORM select
    q = select(Todo)
    if owner_id is not None:
        q = q.where(Todo.owner_id == owner_id)
    if is_done is not None:
        q = q.where(Todo.is_done == is_done)
    # sorting
    col = getattr(Todo, sort_by, None)
    if col is not None:
        q = q.order_by(desc(col) if sort_desc else asc(col))
    q = q.offset(skip).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()


@todos_router.get("/todos/{todo_id}", response_model=TodoRead)
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


@todos_router.patch("/todos/{todo_id}", response_model=TodoRead)
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
    # manage completed metadata when is_done toggles
    if payload.is_done is not None:
        if payload.is_done:
            todo.completed_at = datetime.now(timezone.utc)
            try:
                todo.completed_by = int(current_user["id"])
            except Exception:
                todo.completed_by = None
        else:
            todo.completed_at = None
            todo.completed_by = None
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@todos_router.post("/todos/{todo_id}/complete")
async def complete_todo(
    todo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a todo as completed (owner or admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="Not authorized to modify this todo")
    from datetime import datetime, timezone

    todo.is_done = True
    todo.completed_at = datetime.now(timezone.utc)
    try:
        todo.completed_by = int(current_user["id"])
    except Exception:
        todo.completed_by = None
    todo.updated_at = datetime.now(timezone.utc)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return {"ok": True}


@todos_router.post("/todos/{todo_id}/reopen")
async def reopen_todo(
    todo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a completed todo (owner or admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="Not authorized to modify this todo")
    from datetime import datetime, timezone

    todo.is_done = False
    todo.completed_at = None
    todo.completed_by = None
    todo.updated_at = datetime.now(timezone.utc)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return {"ok": True}



@todos_router.post("/todos/bulk_complete")
async def bulk_complete(
    todo_ids: List[int], current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Bulk mark todos as complete. Only affects todos owned by the caller unless admin."""
    from datetime import datetime, timezone

    q = await db.execute(select(Todo).where(Todo.id.in_(todo_ids)))
    items = q.scalars().all()
    updated = 0
    for t in items:
        if t.owner_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
            continue
        t.is_done = True
        t.completed_at = datetime.now(timezone.utc)
        try:
            t.completed_by = int(current_user["id"])
        except Exception:
            t.completed_by = None
        t.updated_at = datetime.now(timezone.utc)
        db.add(t)
        updated += 1
    await db.commit()
    return {"updated": updated}


@todos_router.post("/todos/{todo_id}/assign")
async def assign_todo(
    todo_id: int, assignee_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Assign a todo to another user (owner or admin)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="Not authorized to assign this todo")
    # lightweight validation: ensure user exists
    u = await get_user_by_id(db, assignee_id)
    if not u:
        raise HTTPException(status_code=404, detail="Assignee not found")
    todo.owner_id = assignee_id
    todo.updated_at = datetime.now(timezone.utc)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return {"ok": True}


@todos_router.post("/todos/{todo_id}/unassign")
async def unassign_todo(
    todo_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Unassign a todo (set owner to current user) - owner or admin only."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if todo.owner_id != int(current_user["id"]) and "admin" not in (current_user.get("scopes") or []):
        raise HTTPException(status_code=403, detail="Not authorized to unassign this todo")
    todo.owner_id = int(current_user["id"])
    todo.updated_at = datetime.now(timezone.utc)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return {"ok": True}


@todos_router.delete("/todos/{todo_id}")
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


# include sub-routers into the public router that main.py imports
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(todos_router)
router.include_router(sessions_router)
router.include_router(admin_router)
