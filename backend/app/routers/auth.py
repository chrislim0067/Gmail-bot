"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
from app.services.audit_service import AuditService
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbSession) -> UserOut:
    auth = AuthService(db)
    try:
        user = await auth.register(body.email, body.password, body.full_name)
    except AuthError as exc:
        if "already" in str(exc).lower():
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await AuditService(db).log(
        action="auth.register",
        resource_type="user",
        user_id=user.id,
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    auth = AuthService(db)
    try:
        user = await auth.authenticate(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token, expires_in = auth.create_access_token(user.id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=expires_in,
    )
    await AuditService(db).log(
        action="auth.login",
        resource_type="user",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie("access_token")


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserUpdate, current_user: CurrentUser, db: DbSession) -> UserOut:
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.timezone is not None:
        current_user.timezone = body.timezone
    await db.flush()
    return UserOut.model_validate(current_user)
