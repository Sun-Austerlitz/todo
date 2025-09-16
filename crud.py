from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from models import Todo, User


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Return a user by email or None."""
    q = await db.execute(select(User).where(User.email == email))
    return q.scalars().first()


async def create_user(db: AsyncSession, user: User):
    """Create a user in the database and return the refreshed object."""
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_todo_by_id(db: AsyncSession, todo_id: int) -> Optional[Todo]:
    q = await db.execute(select(Todo).where(Todo.id == todo_id))
    return q.scalars().first()


async def list_todos(db: AsyncSession) -> List[Todo]:
    """List all todos (simple implementation for demo purposes)."""
    q = await db.execute(select(Todo))
    return q.scalars().all()


async def create_todo(db: AsyncSession, todo: Todo):
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, todo: Todo):
    await db.delete(todo)
    await db.commit()
