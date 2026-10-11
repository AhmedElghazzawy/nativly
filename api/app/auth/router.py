from fastapi import APIRouter, HTTPException, status

from app.auth import service
from app.auth.dependencies import CurrentUser, SessionDep, SettingsDep
from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep) -> UserRead:
    try:
        user = await service.register_user(session, body.email, body.password)
    except service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        ) from None
    return UserRead.model_validate(user)


@router.post("/login")
async def login(body: LoginRequest, session: SessionDep, settings: SettingsDep) -> TokenPair:
    try:
        user = await service.authenticate(session, body.email, body.password)
    except service.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        ) from None
    return await service.issue_tokens(session, user, settings)


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> TokenPair:
    try:
        return await service.rotate_refresh_token(session, body.refresh_token, settings)
    except service.InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        ) from None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, session: SessionDep) -> None:
    await service.revoke_refresh_token(session, body.refresh_token)


@router.get("/me")
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
