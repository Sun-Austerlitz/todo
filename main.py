from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from db import engine
from routes import router as api_router


# suppress noisy passlib bcrypt backend detection logs (reads legacy __about__ attr)
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    title="Todo API",
    description="TODO API with FastAPI and async SQLAlchemy",
)

app.include_router(api_router)
