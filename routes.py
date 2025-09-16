from fastapi import APIRouter, Depends, HTTPException, Security
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import TodoCreate, TodoRead, TodoUpdate
from auth import get_current_user, create_access_token, get_password_hash, verify_password
from crud import get_todo_by_id, list_todos, create_todo as crud_create_todo, get_user_by_email
from db import get_db
from models import Todo, User
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Authenticate: obtain an access token using username and password."""
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token(user.email, user.scopes or [])
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
async def register(email: str, password: str, scopes: List[str] = None, db: AsyncSession = Depends(get_db)):
    """Register a new user (simple implementation)."""
    if await get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = get_password_hash(password)
    user = User(email=email, hashed_password=hashed, scopes=scopes or ["user"])
    db.add(user)
    await db.commit()
    return {"email": email, "scopes": user.scopes}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    """Return information about the current user (from the token)."""
    return current_user


@router.get("/admin")
def admin_only(current_user=Security(get_current_user, scopes=["admin"])):
    """Example endpoint accessible only to administrators."""
    return {"ok": True, "msg": f"Welcome, {current_user['email']}!"}


@router.post("/todos", response_model=TodoRead)
async def create_todo(payload: TodoCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a todo item linked to the current user."""
    # For simplicity, the owner id is derived from the hash of the email. In a real
    # application it's better to store and use a numeric user id.
    todo = Todo(
        title=payload.title,
        description=payload.description,
        owner_id=int(current_user["email"].__hash__() & 0x7FFFFFFF),
    )
    return await crud_create_todo(db, todo)


@router.get("/todos", response_model=List[TodoRead])
async def list_todos_route(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return a list of all todos (simple demonstration)."""
    return await list_todos(db)


@router.get("/todos/{todo_id}", response_model=TodoRead)
async def get_todo(todo_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.patch("/todos/{todo_id}", response_model=TodoRead)
async def update_todo(todo_id: int, payload: TodoUpdate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update a todo item (partial update)."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
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
async def delete_todo(todo_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    await db.delete(todo)
    await db.commit()
    return {"ok": True}
