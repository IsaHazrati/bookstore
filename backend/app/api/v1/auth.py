from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    # ثبت‌نام عمومی همیشه مشتری می‌سازد؛ ادمین فقط با اسکریپت سرور ساخته می‌شود
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
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
def login(data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == data.email))
    ok = verify_password(data.password, user.password_hash if user else None)
    if not (user and ok and user.is_active):
        # پیام یکسان برای ایمیل نامعتبر و رمز اشتباه
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
