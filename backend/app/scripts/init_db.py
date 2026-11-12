"""Bring the database schema up to date with Alembic migrations.

Run from the backend directory: `python -m app.scripts.init_db`. The container runs this
on every start, which is safe because applied migrations are skipped.

Databases created before migrations existed (by `create_all`) already have the original
tables but no migration history. They are stamped at the initial revision first, so only
the newer migrations run.
"""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
INITIAL_REVISION = "0001_initial_schema"


async def _table_names() -> set[str]:
    try:
        async with engine.connect() as connection:
            return set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
    finally:
        # Close the pool inside this event loop; Alembic opens its own connection next.
        await engine.dispose()


def migrate(alembic_config: Config, existing_tables: set[str]) -> None:
    if "users" in existing_tables and "alembic_version" not in existing_tables:
        command.stamp(alembic_config, INITIAL_REVISION)

    command.upgrade(alembic_config, "head")


def main() -> None:
    existing_tables = asyncio.run(_table_names())
    migrate(Config(str(ALEMBIC_INI)), existing_tables)


if __name__ == "__main__":
    main()
