import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="bookstore-test-uploads-"))
# TestClient روی http است؛ کوکی Secure را نمی‌فرستد
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-bytes-long!!")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import Role
from app.models.user import User


@pytest.fixture()
def db_session():
    url = get_settings().db_url
    sqlite = url.get_backend_name() == "sqlite"
    kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}} if sqlite else {}
    engine = create_engine(url, **kwargs)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as s:
        yield s
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(email="u@example.com", password="password123", role=Role.customer, active=True):
        u = User(email=email, password_hash=hash_password(password), role=role, is_active=active)
        db_session.add(u)
        db_session.commit()
        return u

    return _make


def login(client, email, password="password123", keep_cookie=False):
    """ورود. پیش‌فرض کوکی نشست را پاک می‌کند تا تست‌های مبتنی بر Bearer بدون حالت بمانند."""
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if not keep_cookie:
        client.cookies.clear()
    return r


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_h(client, make_user):
    make_user("admin@example.com", role=Role.admin)
    return auth(login(client, "admin@example.com").json()["access_token"])


@pytest.fixture()
def customer_h(client, make_user):
    make_user("cust@example.com")
    return auth(login(client, "cust@example.com").json()["access_token"])
