from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TodoCreate(BaseModel):
    """Schema for creating a todo."""
    title: str = Field(..., min_length=1)
    description: Optional[str] = None


class TodoRead(BaseModel):
    """Schema for reading a todo (API response)."""
    id: int
    title: str
    description: Optional[str]
    owner_id: int
    is_done: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TodoUpdate(BaseModel):
    """Schema for partial updates of a todo."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None


class RefreshRequest(BaseModel):
    """Request body for refreshing access token using a refresh token."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Standard response containing access and refresh tokens."""
    access_token: str
    token_type: str
    refresh_token: str


class LoginRequest(BaseModel):
    """JSON body for username/password login.

    Используется для удобства клиентов (например, curl или fetch) вместо
    application/x-www-form-urlencoded формы OAuth2. Поля: username, password.
    """
    username: str
    password: str
