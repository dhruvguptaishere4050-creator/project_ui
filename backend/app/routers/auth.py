from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, token_is_revoked
from app.models import AuditLog, User
from app.schemas import PasswordChange, Token, UserRead
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE = "sams_refresh"
REFRESH_COOKIE_PATH = "/api/auth"

INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
)


def _token_response(user: User, response: Response) -> Token:
    # The refresh token is never exposed to JavaScript: it lives in an HttpOnly
    # cookie scoped to the auth routes, so XSS cannot exfiltrate a long-lived
    # credential.
    response.set_cookie(
        REFRESH_COOKIE,
        create_refresh_token(str(user.id), user.role.value, user.token_version),
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )
    return Token(
        access_token=create_access_token(str(user.id), user.role.value, user.token_version),
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
    )


@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    db.add(AuditLog(user_id=user.id, action="login", detail=user.email))
    db.commit()
    return _token_response(user, response)


@router.post("/refresh", response_model=Token)
def refresh(
    response: Response,
    sams_refresh: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Token:
    if not sams_refresh:
        raise INVALID_REFRESH
    decoded = decode_token(sams_refresh, expected_type="refresh")
    if decoded is None:
        raise INVALID_REFRESH
    user = db.get(User, int(decoded["sub"]))
    if user is None or not user.is_active or token_is_revoked(decoded, user):
        raise INVALID_REFRESH
    return _token_response(user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.token_version += 1
    db.add(AuditLog(user_id=current_user.id, action="password_change"))
    db.commit()
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
