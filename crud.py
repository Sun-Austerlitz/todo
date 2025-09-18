from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from models import Todo, User
from models import RefreshToken
from datetime import datetime, timezone


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Вернуть объект User по email или None.

    Используем ORM-select, чтобы получить отображаемый объект модели (не сырые
    столбцы таблицы).
    """
    q = await db.execute(select(User).where(User.email == email))
    return q.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Return User by id or None."""
    q = await db.execute(select(User).where(User.id == user_id))
    return q.scalars().first()


async def create_user(db: AsyncSession, user: User):
    """Создать пользователя в базе и вернуть обновлённый объект.

    Перед сохранением нормализуем поле `scopes`: допускается строка или список,
    но в базе сохраняются только допустимые роли ("user", "admin"). При
    неверном вводе — устанавливаем безопасный дефолт ["user"].
    """
    # Нормализация и валидация ролей
    valid_roles = {"user", "admin"}
    scopes = user.scopes
    if isinstance(scopes, str):
        scopes = [scopes]
    if not isinstance(scopes, list):
        scopes = ["user"]
    scopes = [s for s in scopes if s in valid_roles]
    if not scopes:
        scopes = ["user"]
    user.scopes = scopes

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_todo_by_id(db: AsyncSession, todo_id: int) -> Optional[Todo]:
    """Вернуть задачу по id или None."""
    q = await db.execute(select(Todo).where(Todo.id == todo_id))
    return q.scalars().first()


async def list_todos(db: AsyncSession, owner_id: Optional[int] = None) -> List[Todo]:
    """Вернуть список задач. Если указан owner_id, вернуть только задачи этого
    владельца.

    Реализация оставлена максимально простой — роуты делают scope-логику
    (показывать все для админа или по владельцу для обычного пользователя).
    """
    if owner_id is None:
        q = await db.execute(select(Todo))
    else:
        q = await db.execute(select(Todo).where(Todo.owner_id == owner_id))
    return q.scalars().all()


async def create_todo(db: AsyncSession, todo: Todo):
    """Сохранить новую задачу и вернуть обновлённый объект."""
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, todo: Todo):
    """Удалить задачу из базы."""
    await db.delete(todo)
    await db.commit()


async def create_refresh_token(db: AsyncSession, token: RefreshToken):
    """Сохранить запись refresh token и вернуть её."""
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> Optional[RefreshToken]:
    q = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return q.scalars().first()


async def revoke_refresh_token(db: AsyncSession, token: RefreshToken):
    token.revoked = True
    token.last_used_at = datetime.now(timezone.utc)
    db.add(token)
    await db.commit()


async def list_refresh_tokens_for_user(db: AsyncSession, user_id: int):
    q = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    return q.scalars().all()


async def revoke_all_refresh_tokens_for_user(db: AsyncSession, user_id: int):
    q = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    tokens = q.scalars().all()
    for t in tokens:
        t.revoked = True
        t.last_used_at = datetime.now(timezone.utc)
        db.add(t)
    await db.commit()
