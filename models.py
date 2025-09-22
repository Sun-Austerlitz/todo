from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from db import Base
from sqlalchemy.orm import relationship


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
    # owner_id — внешний ключ на users.id для поддержания целостности данных.
    # Для упрощения удаления аккаунтов и автоматической очистки связанных
    # задач используем ON DELETE CASCADE: при удалении пользователя все
    # связанные todos будут удалены автоматически.
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="todos")
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    # When the task was completed (nullable)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Who completed the task (nullable FK to users)
    completed_by = Column(Integer, nullable=True)


class RefreshToken(Base):
    """Модель для stateful refresh tokens.

    Храним хэш токена, метаданные и статус ревока/ротации.
    """
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    # user_id — внешний ключ на users.id. Для refresh-токенов безопасно
    # применять CASCADE: при удалении пользователя связанные refresh-токены
    # удаляются автоматически.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", back_populates="refresh_tokens")
    token_hash = Column(String, nullable=False, unique=True, index=True)
    issued_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, default=False)
    device_id = Column(String, nullable=True)
    # device_type indicates category of client ('web','mobile','desktop', etc.)
    device_type = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    replaced_by_id = Column(Integer, nullable=True)


# Relationships defined on User for ORM convenience
User.todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan", passive_deletes=True)
User.refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
