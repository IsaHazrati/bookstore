from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.models.enums import Role
from tests.conftest import auth, login

REG = "/api/v1/auth/register"


def test_register_creates_customer_without_leaking_hash(client):
    r = client.post(REG, json={"email": "A@Example.com", "password": "password123", "full_name": "Ali"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert body["role"] == "customer"
    assert "password" not in body and "password_hash" not in body


def test_register_cannot_choose_admin_role(client):
    r = client.post(REG, json={"email": "x@example.com", "password": "password123", "role": "admin"})
    assert r.status_code == 201
    assert r.json()["role"] == "customer"


def test_register_duplicate_email_is_case_insensitive(client):
    client.post(REG, json={"email": "a@example.com", "password": "password123"})
    r = client.post(REG, json={"email": "A@EXAMPLE.COM", "password": "password123"})
    assert r.status_code == 409


def test_register_validation(client):
    assert client.post(REG, json={"email": "a@example.com", "password": "short"}).status_code == 422
    assert client.post(REG, json={"email": "not-an-email", "password": "password123"}).status_code == 422


def test_login_success_and_me(client, make_user):
    make_user("a@example.com")
    r = login(client, "a@example.com")
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    me = client.get("/api/v1/auth/me", headers=auth(r.json()["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"


def test_login_failures_share_one_message(client, make_user):
    make_user("a@example.com")
    bad_pw = login(client, "a@example.com", "wrong-password")
    no_user = login(client, "nobody@example.com")
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json() == no_user.json()


def test_inactive_user_cannot_login_or_use_token(client, make_user, db_session):
    u = make_user("a@example.com")
    token = login(client, "a@example.com").json()["access_token"]
    u.is_active = False
    db_session.commit()
    assert login(client, "a@example.com").status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_me_rejects_missing_garbage_and_expired_tokens(client, make_user):
    u = make_user("a@example.com")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth("garbage")).status_code == 401
    s = get_settings()
    expired = jwt.encode(
        {"sub": str(u.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        s.secret_key,
        algorithm=s.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth(expired)).status_code == 401


def test_token_signed_with_other_key_is_rejected(client, make_user):
    u = make_user("a@example.com")
    forged = jwt.encode(
        {"sub": str(u.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "some-other-secret-key-32-bytes-long-xxxxx",
        algorithm="HS256",
    )
    assert client.get("/api/v1/auth/me", headers=auth(forged)).status_code == 401


def test_admin_routes_require_admin_role(client, make_user):
    make_user("c@example.com")
    make_user("adm@example.com", role=Role.admin)
    assert client.get("/api/admin/ping").status_code == 401
    cust = login(client, "c@example.com").json()["access_token"]
    assert client.get("/api/admin/ping", headers=auth(cust)).status_code == 403
    adm = login(client, "adm@example.com").json()["access_token"]
    assert client.get("/api/admin/ping", headers=auth(adm)).json() == {"scope": "admin"}


def test_role_change_takes_effect_on_existing_token(client, make_user, db_session):
    u = make_user("adm@example.com", role=Role.admin)
    token = login(client, "adm@example.com").json()["access_token"]
    u.role = Role.customer
    db_session.commit()
    assert client.get("/api/admin/ping", headers=auth(token)).status_code == 403


def test_admin_token_lives_shorter_than_customer_token(client, make_user):
    make_user("c@example.com")
    make_user("adm@example.com", role=Role.admin)
    cust = login(client, "c@example.com").json()["expires_in"]
    adm = login(client, "adm@example.com").json()["expires_in"]
    assert adm == get_settings().admin_token_minutes * 60
    assert adm < cust


def test_old_argon2_hash_still_works_and_is_upgraded(client, db_session):
    from pwdlib import PasswordHash

    from app.models.user import User

    old = PasswordHash.recommended().hash("password123")  # پارامترهای قدیمی (m=65536)
    u = User(email="old@example.com", password_hash=old, role=Role.customer)
    db_session.add(u)
    db_session.commit()
    assert login(client, "old@example.com").status_code == 200
    db_session.refresh(u)
    assert "m=19456" in u.password_hash and u.password_hash != old
    assert login(client, "old@example.com").status_code == 200


def test_login_returns_503_when_hashing_slots_are_exhausted(client, make_user, monkeypatch):
    import threading

    from app.core import security

    make_user("a@example.com")
    monkeypatch.setattr(security, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(security, "_SLOT_TIMEOUT_SECONDS", 0.05)
    security._slots.acquire()  # همه‌ی اسلات‌ها مشغول
    try:
        r = login(client, "a@example.com")
        assert r.status_code == 503 and r.headers["retry-after"] == "5"
        r = client.post("/api/v1/auth/register", json={"email": "n@example.com", "password": "password123"})
        assert r.status_code == 503
    finally:
        security._slots.release()
    assert login(client, "a@example.com").status_code == 200
