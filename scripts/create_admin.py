"""Idempotent admin-creation script.

Запускайте вручную в project's venv. Скрипт не выполняется автоматически.
Пример использования:
    uv run python scripts/create_admin.py

Скрипт проверяет, существует ли пользователь с данным email; если нет — создает
администратора с указанным паролем. Пароль хэшируется с помощью passlib/Argon2.
"""
import asyncio
import os
import getpass

from sqlalchemy import text
from db import async_session
from models import User
from auth import get_password_hash


async def ensure_admin(email: str, password: str):
    async with async_session() as session:
        existing = await session.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        row = existing.first()
        if row:
            print("Admin already exists (no change)")
            return
        hashed = get_password_hash(password)
        user = User(email=email, hashed_password=hashed, scopes=["admin"], is_active=True)
        session.add(user)
        await session.commit()
        print("Admin created")


if __name__ == "__main__":
    email = os.environ.get("ADMIN_EMAIL") or input("admin email: ")
    pw = os.environ.get("ADMIN_PASSWORD")
    if not pw:
        pw = getpass.getpass("admin password: ")
    asyncio.run(ensure_admin(email, pw))
