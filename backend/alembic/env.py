from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (ثبت همه‌ی مدل‌ها روی Base.metadata)
from app.core.config import get_settings
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# آدرس دیتابیس مستقیم از تنظیمات برنامه ساخته می‌شود و از alembic.ini عبور نمی‌کند:
# configparser کاراکتر % را به‌عنوان interpolation تفسیر می‌کند و رمزهای دارای % را خراب می‌کرد.
DB_URL = get_settings().db_url


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
