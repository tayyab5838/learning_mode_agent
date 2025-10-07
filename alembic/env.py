from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import os
from dotenv import load_dotenv
from app.utils.db import Base  # <-- import your Base
from app.models import models  # <-- import all models so Alembic sees them  # noqa: F401

# Load env variables
load_dotenv()

# Alembic Config object
config = context.config

# Optionally, override URL from .env
DATABASE_URL = os.getenv("DATABASE_URL").replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
