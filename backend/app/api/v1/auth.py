from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps.auth import AUTH_COOKIE, get_current_user
from app.core.config import get_settings
from app.core.security import PasswordHashingBusy, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_BUSY = HTTPException(
    status.HTTP_503_SERVICE_UNAVAILABLE, "server busy, try again shortly", headers={"Retry-After": "5"}
)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    # ثبت‌نام عمومی همیشه مشتری می‌سازد؛ ادمین فقط با اسکریپت سرور ساخته می‌شود
    try:
        password_hash = hash_password(data.password)
    except PasswordHashingBusy:
        raise _BUSY
    user = User(
        email=data.email,
        password_hash=password_hash,
        full_name=data.full_name,
        role=Role.customer,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # ثبت‌نام همزمان با همان ایمیل
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == data.email))
    try:
        ok, new_hash = verify_password(data.password, user.password_hash if user else None)
    except PasswordHashingBusy:
        raise _BUSY
    if not (user and ok and user.is_active):
        # پیام یکسان برای ایمیل نامعتبر و رمز اشتباه
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if new_hash:  # هش با پارامترهای قدیمی بود؛ بی‌صدا ارتقا می‌دهیم
        user.password_hash = new_hash
        db.commit()
    token, expires_in = create_access_token(user.id, user.role)
    # فروشگاه از کوکی HttpOnly استفاده می‌کند (جاوااسکریپت به توکن دسترسی ندارد)؛
    # پنل ادمین همچنان توکن بدنه را به‌صورت Bearer می‌فرستد.
    response.set_cookie(
        AUTH_COOKIE, token, max_age=expires_in, httponly=True,
        secure=get_settings().cookie_secure, samesite="lax", path="/",
    )
    return TokenOut(access_token=token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(AUTH_COOKIE, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
