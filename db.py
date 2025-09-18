from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# URL подключения к базе данных. Можно переопределить через переменную окружения
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://todo:todo@localhost:5432/todo"
)

# Асинхронный движок SQLAlchemy и фабрика сессий
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def get_db():
    """Зависимость FastAPI, возвращающая асинхронную сессию БД.

    Пример использования в роутере:
        db: AsyncSession = Depends(get_db)

    Сессия автоматически закрывается при выходе из контекста.
    """
    async with AsyncSessionLocal() as session:
        yield session
