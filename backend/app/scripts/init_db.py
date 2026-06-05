import asyncio

from app.core.database import create_database_tables


async def main() -> None:
    await create_database_tables()


if __name__ == "__main__":
    asyncio.run(main())
