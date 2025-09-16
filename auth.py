import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import User

SECRET_KEY = os.environ.get("SECRET_KEY", "top_secret")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_EXPIRE_MINUTES = int(os.environ.get("ACCESS_EXPIRE_MINUTES", "10"))

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    deprecated="auto",
    # conservative Argon2 settings (tune for production hardware):
    argon2__time_cost=2,
    argon2__memory_cost=65536,  # in KiB (64 MB)
    argon2__parallelism=2,
)

oauth_scheme = OAuth2PasswordBearer(
    tokenUrl="/token", scopes={"user": "Usual access", "admin": "Full access"}
)


def get_password_hash(password: str) -> str:
    """Return bcrypt hash for a password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, scopes: List[str]) -> str:
    """Create a JWT access token with the given scopes."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "scopes": scopes,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    q = await db.execute(User.__table__.select().where(User.email == email))
    return q.scalars().first()


async def get_current_user(
    security_scopes: SecurityScopes, token: str = Depends(oauth_scheme), db: AsyncSession = Depends(get_db)
):
    """Dependency that returns the current authenticated user.

    Validates the JWT, expiration, token type and required scopes.
    Returns a dict like {"email": ..., "scopes": [...]}.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="token [invalid | expired]")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="token [invalid | expired]")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="token [invalid | expired]")

    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive or unknown user")

    required = set(security_scopes.scopes)
    token_scopes = set(payload.get("scopes", []))
    if required and not required.issubset(token_scopes):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return {"email": email, "scopes": list(token_scopes)}
