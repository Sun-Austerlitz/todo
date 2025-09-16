from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from datetime import datetime, timezone
from db import Base


class User(Base):
    """User model.

    Fields:
    - email: unique identifier
    - hashed_password: password (stored as a hash)
    - is_active: active flag
    - scopes: list of user roles/permissions
    - created_at / updated_at: timestamps
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    scopes = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class Todo(Base):
    """Todo model.

    Fields:
    - title, description: todo content
    - owner_id: owner's id (simplified as int here)
    - is_done: status flag
    - created_at / updated_at: timestamps
    """
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, nullable=False)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
