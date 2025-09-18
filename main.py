from fastapi import FastAPI
from contextlib import asynccontextmanager

from db import engine
from routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan hook: освобождение ресурсов при shutdown.

    Явно вызываем engine.dispose() для аккуратного закрытия пула.
    """
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, title="Todo API", description="Async FastAPI + SQLAlchemy")

# Подключаем маршруты из модуля routes.py
app.include_router(api_router)
