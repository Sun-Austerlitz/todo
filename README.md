# Todo (FastAPI)

Минимальное async FastAPI приложение, разделённое на модули: `db`, `models`, `schemas`, `crud`, `auth`, `routes`, `main`.

Инструкции по миграциям
- Этот проект использует Alembic для управления схемой базы данных (папка `alembic/`).
- Никогда не используйте `Base.metadata.create_all` в продакшене. Всю работу по изменению схемы выполняют миграции.

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
- Для разработческой среды создавайте простые, воспроизводимые миграции и применяйте их локально.
- Если нужно быстро восстановить схему для тестов, используйте миграции или отдельные SQL-скрипты/fixtures,
  но не включайте автосоздание схемы в код приложения. Это мешает согласованности схемы между окружениями.

Пример запуска приложения (локально):

```bash
export DATABASE_URL=postgresql+asyncpg://todo:todo@localhost:5432/todo
uvicorn main:app --reload

Developer helpers
-----------------

To create a local admin user safely, use the `scripts/create_superadmin.py` helper.

Example (interactive):

    python3 scripts/create_superadmin.py

Non-interactive (CI / one-off, reads password from env):

    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD="$ADMIN_PASSWORD" python3 scripts/create_superadmin.py -y

Notes:
- The script will refuse to run if `ENV=production` unless `--force` is passed.
- Do not commit passwords to git. Prefer passing passwords via CI secrets or interactive prompt.
```

Если нужна помощь с Alembic (конфиг, env.py, привязка к async engine) — откройте issue или напишите, могу добавить
пример конфигурации и шаблоны миграций.
