# Todo (FastAPI)

Минимальное async FastAPI приложение, разделённое на модули: `db`, `models`, `schemas`, `crud`, `auth`, `routes`, `main`.

Инструкции по миграциям

Пример: создать и применить миграции

```bash
# Если проект ещё не настроен для alembic (папка alembic уже есть в этом репозитории,
# пропустите инициализацию). В противном случае:
alembic init alembic

# Создать миграцию на основе текущих моделей (авто-генерация):
alembic revision --autogenerate -m "initial"

# Применить миграции к базе данных:
alembic upgrade head
```

Локальная разработка — правильный подход
  но не включайте автосоздание схемы в код приложения. Это мешает согласованности схемы между окружениями.

Пример запуска приложения (локально):

```bash
export DATABASE_URL=postgresql+asyncpg://todo:todo@localhost:5432/todo
uvicorn main:app --reload

Developer helpers

To create a local admin user safely, use the `scripts/create_superadmin.py` helper.

Example (interactive):

    python3 scripts/create_superadmin.py

Non-interactive (CI / one-off, reads password from env):

    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD="$ADMIN_PASSWORD" python3 scripts/create_superadmin.py -y

Notes:

Development
-----------

Start a local development environment with Postgres and Redis:

```sh
docker-compose -f docker-compose.dev.yml up --build
```

Run tests locally (requires dependencies):

```sh
PYTHONPATH=. python -m pytest -q
```

```

Если нужна помощь с Alembic (конфиг, env.py, привязка к async engine) — откройте issue или напишите, могу добавить
пример конфигурации и шаблоны миграций.
