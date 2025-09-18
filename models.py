from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from datetime import datetime, timezone
from db import Base


class User(Base):
    """Модель пользователя.

    Поля:
    - email: уникальный идентификатор пользователя
    - hashed_password: хэш пароля
    - is_active: флаг активности аккаунта
    - scopes: список ролей/прав пользователя (JSON)
    - created_at / updated_at: метки времени
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    # адрес электронной почты — уникальный идентификатор
    email = Column(String, unique=True, index=True, nullable=False)
    # храним пароль только в виде безопасного хэша
    hashed_password = Column(String, nullable=False)
    # активность аккаунта (можно отключить пользователя)
    is_active = Column(Boolean, default=True)
    # scopes хранится как JSON-список строк ролей. По умолчанию новый пользователь
    # получает роль "user". Валидация допустимых ролей выполняется на уровне
    # приложения (см. `crud.create_user`).
    scopes = Column(JSON, default=lambda: ["user"])
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class Todo(Base):
    """Модель задачи (todo).

    Поля:
    - title, description: содержимое задачи
    - owner_id: идентификатор владельца задачи (в текущей реализации — целое число)
    - is_done: признак завершённости
    - created_at / updated_at: метки времени
    """
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # owner_id — числовой идентификатор пользователя (в будущем можно сделать
    # foreign key на users.id для целостности данных)
    owner_id = Column(Integer, nullable=False)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class RefreshToken(Base):
    """Модель для stateful refresh tokens.

    Храним хэш токена, метаданные и статус ревока/ротации.
    """
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    issued_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, default=False)
    device_id = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    replaced_by_id = Column(Integer, nullable=True)
