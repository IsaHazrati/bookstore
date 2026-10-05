import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)
_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid or missing credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized
    # نقش از دیتابیس خوانده می‌شود، نه از توکن: تغییر نقش/غیرفعال‌سازی فوراً اثر می‌کند
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
