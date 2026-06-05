from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    user = User(
        name=user_create.name.strip(),
        email=normalize_email(str(user_create.email)),
        password_hash=hash_password(user_create.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


def authenticate_user(user: User | None, password: str) -> User | None:
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
