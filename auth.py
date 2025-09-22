import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from jose import jwt
from jose.exceptions import JWTError
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import User
import secrets
import hashlib
import hmac

# Отдельный секрет для хэширования refresh token в БД (по возможности
# храните в секрет-менеджере). По умолчанию пытаемся взять REFRESH_TOKEN_SECRET,
# иначе — SECRET_KEY из окружения, иначе безопасный дефолт (но в проде
# обязательно задавайте переменные окружения).
REFRESH_TOKEN_SECRET = os.environ.get("REFRESH_TOKEN_SECRET", os.environ.get("SECRET_KEY", "top_secret"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("REFRESH_EXPIRE_DAYS", "30"))


def generate_raw_refresh_token() -> str:
    """Сгенерировать крипто-безопасный raw refresh token (строка).

    Raw токен возвращается клиенту один раз; в базе хранится его HMAC.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(raw: str) -> str:
    """Хэшировать raw refresh token безопасным HMAC-SHA256.

    Возвращаем hex-строку.
    """
    return hmac.new(REFRESH_TOKEN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()


# Настройки JWT: берём из окружения. В продакшне задавайте сильный SECRET_KEY
# и разумное TTL (ACCESS_EXPIRE_MINUTES).
SECRET_KEY = os.environ.get("SECRET_KEY", "top_secret")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_EXPIRE_MINUTES = int(os.environ.get("ACCESS_EXPIRE_MINUTES", "15"))

# Конфигурация хеширования паролей через passlib.
# Используем Argon2 — современный алгоритм KDF, подходящий для новых проектов.
pwd_context = CryptContext(
    schemes=["argon2"],
    default="argon2",
    deprecated="auto",
    # Консервативные параметры Argon2 — выставьте по нагрузке/железу в проде
    argon2__time_cost=2,
    argon2__memory_cost=65536,  # в KiB (64 MB)
    argon2__parallelism=2,
)

# OAuth2 схема для endpoints: tokenUrl указывает endpoint получения токена
# Use simple HTTP Bearer token for documentation/UI (Swagger "Authorize" will
# show a single Bearer token input). We no longer advertise an OAuth2 password
# flow in OpenAPI — the API accepts JSON login at /token and expects a Bearer
# access token in Authorization header for protected endpoints.
bearer_scheme = HTTPBearer()


def get_password_hash(password: str) -> str:
    """Вернуть хэш пароля (Argon2 через passlib).

    Контракт: на вход — plain str, на выходе — безопасный хэш, который можно
    хранить в БД. Хэширование — дорогостоящая операция; вызывайте асинхронно
    в фоне при необходимости (зависит от вашей архитектуры).
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверить plain-пароль против хэша."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, scopes: List[str]) -> str:
    """Сгенерировать access JWT.

    Контракт: возвращается компактный HS256-токен с полями:
    - sub: идентификатор субъекта (email)
    - scopes: список ролей
    - type: 'access' (отдельяем от возможных refresh токенов)
    - iat, exp: временные метки

    Примечание: refresh token пока не реализован — см. рекомендации в docs/.
    """
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
    """Вернуть объект User по email или None.

    Используем ORM-select, чтобы получить отображаемый объект модели (не сырые
    значения таблицы).
    """
    from sqlalchemy import select

    q = await db.execute(select(User).where(User.email == email))
    return q.scalars().first()


async def get_current_user(
    security_scopes: SecurityScopes,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Зависимость FastAPI — вернуть текущего аутентифицированного пользователя.

    Проверяет токен (валиден ли, не просрочен, правильного типа) и наличие
    требуемых скоупов. Возвращает компактный «принципал» в виде словаря:
    {"id": ..., "email": ..., "scopes": [...]}
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        # Access token expired — client should attempt refresh
        headers = {"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'}
        raise HTTPException(status_code=401, detail="access token expired", headers=headers)
    except JWTError:
        headers = {"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token is invalid"'}
        raise HTTPException(status_code=401, detail="access token invalid", headers=headers)
    if payload.get("type") != "access":
        headers = {"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token is not an access token"'}
        raise HTTPException(status_code=401, detail="token invalid type", headers=headers)

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="token [invalid | expired]")

    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        # Не сообщаем детали, чтобы не утекала информация о наличии пользователя
        raise HTTPException(status_code=400, detail="Inactive or unknown user")

    # Проверка скоупов: если endpoint требует скоупы — они должны быть в токене
    required = set(security_scopes.scopes)
    token_scopes = set(payload.get("scopes", []))
    if required and not required.issubset(token_scopes):
        # Inform client about insufficient scopes using RFC-style header
        scope_str = " ".join(sorted(required))
        headers = {"WWW-Authenticate": f'Bearer error="insufficient_scope", scope="{scope_str}"'}
        raise HTTPException(status_code=403, detail="Not enough permissions", headers=headers)

    # Compact principal: минимальный JSON-like объект, пригодный для зависимостей
    return {"id": user.id, "email": email, "scopes": list(token_scopes)}
