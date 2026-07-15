from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Load our settings so the real DATABASE_URL is used, not the ini placeholder.
from app.config import settings

# Import all models so autogenerate can see them.
import app.database.models  # noqa: F401
from app.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Normalize the driver to psycopg (v3). The .env uses the bare `postgresql://`
# scheme which SQLAlchemy routes to psycopg2; we only have psycopg v3 installed.
db_url = settings.database_url.replace(
    "postgresql://", "postgresql+psycopg://", 1
).replace(
    "postgres://", "postgresql+psycopg://", 1
)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
