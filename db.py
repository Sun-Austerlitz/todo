from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Database connection URL. Can be overridden via environment variable.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://todo:todo@localhost:5432/todo"
)

# Asynchronous SQLAlchemy engine and session factory
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def get_db():
    """FastAPI dependency that yields an async database session.

    Example usage in a router:
        db: AsyncSession = Depends(get_db)

    The session is automatically closed when leaving the context.
    """
    async with AsyncSessionLocal() as session:
        yield session
