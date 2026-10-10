from app.core.config import get_settings
from app.models.enums import Role
from tests.conftest import login

CSRF = {"X-Requested-With": "fetch"}


def test_login_sets_httponly_lax_cookie_and_me_works_with_cookie_only(client, make_user):
    make_user("a@example.com")
    r = login(client, "a@example.com", keep_cookie=True)
    cookie = r.headers["set-cookie"].lower()
    assert "access_token=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    me = client.get("/api/v1/auth/me")  # بدون هدر Authorization؛ فقط کوکی
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"


def test_cookie_is_secure_by_default(client, make_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "cookie_secure", True)
    make_user("a@example.com")
    assert "secure" in login(client, "a@example.com", keep_cookie=True).headers["set-cookie"].lower()


def test_unsafe_request_with_cookie_requires_csrf_header(client, make_user):
    make_user("adm@example.com", role=Role.admin)
    login(client, "adm@example.com", keep_cookie=True)
    r = client.post("/api/admin/categories", json={"name": "x"})
    assert r.status_code == 403 and "X-Requested-With" in r.json()["detail"]
    assert client.post("/api/admin/categories", json={"name": "x"}, headers=CSRF).status_code == 201
    assert client.get("/api/admin/categories").status_code == 200  # GET نیازی ندارد


def test_bearer_requests_do_not_need_csrf_header(client, make_user):
    make_user("adm@example.com", role=Role.admin)
    token = login(client, "adm@example.com").json()["access_token"]
    client.cookies.clear()
    r = client.post("/api/admin/categories", json={"name": "y"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201


def test_logout_clears_cookie(client, make_user):
    make_user("a@example.com")
    login(client, "a@example.com", keep_cookie=True)
    assert client.get("/api/v1/auth/me").status_code == 200
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 204 and "access_token=" in r.headers["set-cookie"] and "max-age=0" in r.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").status_code == 401
