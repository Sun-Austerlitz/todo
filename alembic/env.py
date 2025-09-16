import asyncio
import os
import sys
from logging.config import fileConfig

# ensure project root on sys.path so imports like `from db import ...` work
# (must be done before importing project modules)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from db import DATABASE_URL, Base  # noqa: E402
from models import *  # noqa: F401,F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your project's DATABASE_URL and metadata
# Ensure db.py exposes DATABASE_URL and Base, and models are imported so metadata is populated


target_metadata = Base.metadata


def run_migrations_offline():
    url = os.environ.get("DATABASE_URL", DATABASE_URL)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    url = os.environ.get("DATABASE_URL", DATABASE_URL)
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
