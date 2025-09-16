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
