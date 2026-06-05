from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    MessageResponse,
    ProtectedResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.user_service import authenticate_user, create_user, get_user_by_email

router = APIRouter()


def serialize_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


def set_auth_cookie(response: Response, access_token: str) -> None:
    settings = get_settings()
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    existing_user = await get_user_by_email(session, str(user_create.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = await create_user(session, user_create)
    access_token = create_access_token(subject=str(user.id))
    set_auth_cookie(response, access_token)

    return AuthResponse(user=serialize_user(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    user_login: UserLogin,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    user = await get_user_by_email(session, str(user_login.email))
    authenticated_user = authenticate_user(user, user_login.password)

    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(subject=str(authenticated_user.id))
    set_auth_cookie(response, access_token)

    return AuthResponse(user=serialize_user(authenticated_user))


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    return serialize_user(current_user)


@router.get("/protected", response_model=ProtectedResponse)
async def protected_route(current_user: User = Depends(get_current_user)) -> ProtectedResponse:
    return ProtectedResponse(
        message="You are authenticated",
        user=serialize_user(current_user),
    )
