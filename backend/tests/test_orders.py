import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.catalog import Book
from app.models.digital_access import DigitalAccess
from app.models.enums import Role
from app.models.order import Order
from tests.conftest import auth, login

A, V = "/api/admin", "/api/v1"
PDF = b"%PDF-1.7\n" + b"0" * 64
SHIP = {"recipient_name": "علی رضایی", "phone": "۰۹۱۲ ۱۲۳ ۴۵۶۷", "province": "تهران", "city": "تهران",
        "address": "خیابان آزادی، پلاک ۱"}


@pytest.fixture(autouse=True)
def shop_settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "shipping_fee_rial", 500000)
    monkeypatch.setattr(s, "max_downloads_per_book", 3)


def mk_book(client, h, title="بوف کور", book_type="physical", price=1200000, stock=5, isbn=None):
    r = client.post(f"{A}/books", headers=h, json={"title": title, "author": "هدایت", "book_type": book_type,
                                                    "price": price, "stock_quantity": stock, "isbn": isbn})
    assert r.status_code == 201, r.text
    b = r.json()
    if book_type != "physical":
        assert client.post(f"{A}/books/{b['id']}/digital-file", headers=h, files={"file": ("b.pdf", PDF)}).status_code == 200
    r = client.put(f"{A}/books/{b['id']}", headers=h, json={"title": title, "author": "هدایت", "book_type": book_type,
                                                           "price": price, "stock_quantity": stock, "isbn": isbn,
                                                           "is_published": True})
    assert r.status_code == 200, r.text
    return r.json()


def place(client, h, items, shipping=SHIP, expect=201):
    body = {"items": items}
    if shipping is not None:
        body["shipping"] = shipping
    r = client.post(f"{V}/orders", headers=h, json=body)
    assert r.status_code == expect, r.text
    return r.json()


def stock(db_session, book_id):
    db_session.expire_all()
    return db_session.get(Book, book_id).stock_quantity


@pytest.fixture()
def other_h(client, make_user):
    make_user("other@example.com")
    return auth(login(client, "other@example.com").json()["access_token"])


# ---------- ثبت سفارش ----------
def test_physical_order_uses_server_prices_and_reserves_stock(client, admin_h, customer_h, db_session):
    b = mk_book(client, admin_h, stock=5)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical", "quantity": 2, "unit_price": 1}])
    assert o["status"] == "pending_payment"
    assert o["items"][0]["unit_price"] == "1200000" and o["items"][0]["title"] == "بوف کور"
    assert (o["subtotal"], o["shipping_fee"], o["total_price"]) == ("2400000", "500000", "2900000")
    assert o["phone"] == "09121234567" and o["recipient_name"] == "علی رضایی"
    assert o["expires_at"] is not None and o["items"][0]["book_slug"] == b["slug"]
    assert stock(db_session, b["id"]) == 3


def test_digital_only_order_needs_no_shipping_and_no_fee(client, admin_h, customer_h):
    d = mk_book(client, admin_h, title="کیهان", book_type="digital")
    o = place(client, customer_h, [{"book_id": d["id"], "item_type": "digital"}], shipping=None)
    assert (o["shipping_fee"], o["total_price"], o["recipient_name"]) == ("0", "1200000", None)


@pytest.mark.parametrize("case", ["no_shipping", "unpublished", "no_print", "no_digital", "digital_qty", "dup",
                                  "too_many", "bad_phone", "empty"])
def test_order_validation(client, admin_h, customer_h, case):
    p = mk_book(client, admin_h, title="چاپی", isbn="1")
    d = mk_book(client, admin_h, title="دیجیتال", book_type="digital", isbn="2")
    draft = client.post(f"{A}/books", headers=admin_h, json={"title": "پیش", "author": "a", "book_type": "physical",
                                                              "price": 1, "stock_quantity": 9}).json()
    phys = {"book_id": p["id"], "item_type": "physical"}
    items, shipping, code = {
        "no_shipping": ([phys], None, 422),
        "unpublished": ([{"book_id": draft["id"], "item_type": "physical"}], SHIP, 422),
        "no_print": ([{"book_id": d["id"], "item_type": "physical"}], SHIP, 422),
        "no_digital": ([{"book_id": p["id"], "item_type": "digital"}], None, 422),
        "digital_qty": ([{"book_id": d["id"], "item_type": "digital", "quantity": 2}], None, 422),
        "dup": ([phys, phys], SHIP, 422),
        "too_many": ([{**phys, "quantity": 11}], SHIP, 422),
        "bad_phone": ([phys], {**SHIP, "phone": "12345"}, 422),
        "empty": ([], SHIP, 422),
    }[case]
    place(client, customer_h, items, shipping=shipping, expect=code)


def test_out_of_stock_rolls_back_the_whole_order(client, admin_h, customer_h, db_session):
    a = mk_book(client, admin_h, title="الف", stock=5, isbn="1")
    b = mk_book(client, admin_h, title="ب", stock=1, isbn="2")
    r = client.post(f"{V}/orders", headers=customer_h, json={"shipping": SHIP, "items": [
        {"book_id": a["id"], "item_type": "physical", "quantity": 2},
        {"book_id": b["id"], "item_type": "physical", "quantity": 2}]})
    assert r.status_code == 409 and "ب" in r.json()["detail"]
    assert stock(db_session, a["id"]) == 5 and stock(db_session, b["id"]) == 1
    assert db_session.scalar(select(Order.id)) is None


def test_orders_are_private(client, admin_h, customer_h, other_h):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    assert client.get(f"{V}/orders/{o['id']}", headers=other_h).status_code == 404
    assert client.post(f"{V}/orders/{o['id']}/payment", headers=other_h, json={"reference": "123456"}).status_code == 404
    assert client.post(f"{V}/orders/{o['id']}/cancel", headers=other_h).status_code == 404
    assert client.get(f"{V}/orders", headers=other_h).json()["total"] == 0
    assert client.get(f"{V}/orders", headers=customer_h).json()["total"] == 1
    assert client.get(f"{V}/orders").status_code == 401


# ---------- پرداخت، لغو، انقضا ----------
def test_payment_submission_and_correction(client, admin_h, customer_h):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    r = client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": " ۱۲۳۴۵۶ "})
    assert r.json()["status"] == "awaiting_confirmation" and r.json()["payment_reference"] == "123456"
    r = client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": "654321"})
    assert r.json()["status"] == "awaiting_confirmation" and r.json()["payment_reference"] == "654321"
    assert client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": "12"}).status_code == 422


def test_customer_cancel_restores_stock_only_before_payment(client, admin_h, customer_h, db_session):
    b = mk_book(client, admin_h, stock=3)
    o1 = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical", "quantity": 2}])
    assert stock(db_session, b["id"]) == 1
    r = client.post(f"{V}/orders/{o1['id']}/cancel", headers=customer_h)
    assert r.json()["status"] == "cancelled" and r.json()["cancel_reason"] == "cancelled by customer"
    assert stock(db_session, b["id"]) == 3
    assert client.post(f"{V}/orders/{o1['id']}/cancel", headers=customer_h).status_code == 409  # دوباره
    o2 = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    client.post(f"{V}/orders/{o2['id']}/payment", headers=customer_h, json={"reference": "123456"})
    assert client.post(f"{V}/orders/{o2['id']}/cancel", headers=customer_h).status_code == 409
    assert client.post(f"{V}/orders/{o1['id']}/payment", headers=customer_h, json={"reference": "123456"}).status_code == 409


def test_unpaid_orders_expire_and_release_stock(client, admin_h, customer_h, db_session):
    b = mk_book(client, admin_h, stock=2)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical", "quantity": 2}])
    assert stock(db_session, b["id"]) == 0
    order = db_session.get(Order, o["id"])
    order.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    r = client.get(f"{V}/orders/{o['id']}", headers=customer_h).json()
    assert r["status"] == "cancelled" and r["cancel_reason"] == "payment deadline passed"
    assert stock(db_session, b["id"]) == 2
    assert client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": "123456"}).status_code == 409


def test_submitted_payment_is_not_expired(client, admin_h, customer_h, db_session):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": "123456"})
    order = db_session.get(Order, o["id"])
    order.expires_at = datetime.now(timezone.utc) - timedelta(days=3)
    db_session.commit()
    assert client.get(f"{V}/orders/{o['id']}", headers=customer_h).json()["status"] == "awaiting_confirmation"


# ---------- ادمین ----------
def test_admin_physical_lifecycle_and_invalid_transitions(client, admin_h, customer_h):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    oid = o["id"]
    assert client.post(f"{A}/orders/{oid}/ship", headers=admin_h, json={}).status_code == 409
    assert client.post(f"{A}/orders/{oid}/complete", headers=admin_h).status_code == 409
    client.post(f"{V}/orders/{oid}/payment", headers=customer_h, json={"reference": "998877"})
    r = client.post(f"{A}/orders/{oid}/confirm-payment", headers=admin_h).json()
    assert r["status"] == "paid" and r["paid_at"] and r["user_email"] == "cust@example.com"
    assert client.post(f"{A}/orders/{oid}/confirm-payment", headers=admin_h).status_code == 409
    r = client.post(f"{A}/orders/{oid}/ship", headers=admin_h, json={"tracking_code": "۱۲۳۴۵۶۷۸۹"}).json()
    assert r["status"] == "shipped" and r["tracking_code"] == "123456789"
    assert client.post(f"{A}/orders/{oid}/cancel", headers=admin_h, json={"reason": "x y"}).status_code == 409
    assert client.post(f"{A}/orders/{oid}/complete", headers=admin_h).json()["status"] == "completed"


def test_admin_reject_payment_gives_new_deadline(client, admin_h, customer_h):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    client.post(f"{V}/orders/{o['id']}/payment", headers=customer_h, json={"reference": "111111"})
    r = client.post(f"{A}/orders/{o['id']}/reject-payment", headers=admin_h, json={"reason": "واریزی پیدا نشد"}).json()
    assert r["status"] == "pending_payment" and "واریزی پیدا نشد" in r["admin_note"]
    assert r["expires_at"] > o["expires_at"]
    # مشتری یادداشت ادمین را نمی‌بیند
    assert "admin_note" not in client.get(f"{V}/orders/{o['id']}", headers=customer_h).json()


def test_admin_cancel_paid_order_restores_stock(client, admin_h, customer_h, db_session):
    b = mk_book(client, admin_h, stock=4)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical", "quantity": 3}])
    client.post(f"{A}/orders/{o['id']}/confirm-payment", headers=admin_h)
    r = client.post(f"{A}/orders/{o['id']}/cancel", headers=admin_h, json={"reason": "درخواست مشتری"}).json()
    assert r["status"] == "cancelled" and r["cancel_reason"] == "درخواست مشتری"
    assert stock(db_session, b["id"]) == 4


def test_admin_patch_postal_code_and_notes(client, admin_h, customer_h):
    b = mk_book(client, admin_h)
    o = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    r = client.patch(f"{A}/orders/{o['id']}", headers=admin_h, json={"postal_code": "۱۲۳۴۵-۶۷۸۹۰"})
    assert r.json()["postal_code"] == "1234567890" and r.json()["admin_note"] is None
    r = client.patch(f"{A}/orders/{o['id']}", headers=admin_h, json={"admin_note": "تماس گرفته شد"})
    assert r.json()["postal_code"] == "1234567890" and r.json()["admin_note"] == "تماس گرفته شد"
    assert client.patch(f"{A}/orders/{o['id']}", headers=admin_h, json={"postal_code": "123"}).status_code == 422
    assert client.get(f"{V}/orders/{o['id']}", headers=customer_h).json()["postal_code"] == "1234567890"


def test_admin_list_filters_search_and_summary(client, admin_h, customer_h, other_h):
    b = mk_book(client, admin_h, stock=10)
    o1 = place(client, customer_h, [{"book_id": b["id"], "item_type": "physical"}])
    o2 = place(client, other_h, [{"book_id": b["id"], "item_type": "physical"}], shipping={**SHIP, "phone": "09351112233"})
    client.post(f"{V}/orders/{o2['id']}/payment", headers=other_h, json={"reference": "123456"})
    def ids(**params):
        return [o["id"] for o in client.get(f"{A}/orders", headers=admin_h, params=params).json()["items"]]
    assert ids() == [o2["id"], o1["id"]]
    assert ids(status="awaiting_confirmation") == [o2["id"]]
    assert ids(q="other@") == [o2["id"]] and ids(q="0935") == [o2["id"]] and ids(q=f"#{o1['id']}") == [o1["id"]]
    assert client.get(f"{A}/orders/summary", headers=admin_h).json() == {"awaiting_confirmation": 1, "to_ship": 0}
    assert client.get(f"{A}/orders", headers=customer_h).status_code == 403


# ---------- دیجیتال و دانلود ----------
def _buy_digital(client, admin_h, customer_h, **kw):
    d = mk_book(client, admin_h, title="کیهان", book_type="digital", **kw)
    o = place(client, customer_h, [{"book_id": d["id"], "item_type": "digital"}], shipping=None)
    r = client.post(f"{A}/orders/{o['id']}/confirm-payment", headers=admin_h).json()
    return d, o, r


def test_digital_order_completes_and_downloads(client, admin_h, customer_h):
    d, o, confirmed = _buy_digital(client, admin_h, customer_h)
    assert confirmed["status"] == "completed" and confirmed["completed_at"]
    lib = client.get(f"{V}/me/library", headers=customer_h).json()
    assert [(x["title"], x["file_format"], x["downloads_left"]) for x in lib] == [("کیهان", "PDF", 3)]
    link = client.post(f"{V}/me/library/{lib[0]['access_id']}/link", headers=customer_h).json()
    assert link["url"].startswith("/api/v1/downloads/") and link["expires_in"] == 300 and link["downloads_left"] == 2
    r = client.get(link["url"])  # لینک بدون کوکی/توکن هم کار می‌کند (برای مدیر دانلود)
    assert r.status_code == 200 and r.content == PDF and r.headers["content-type"] == "application/pdf"
    cd = r.headers["content-disposition"]
    assert cd.startswith("attachment;") and "filename*=UTF-8''%DA%A9%DB%8C%D9%87%D8%A7%D9%86.pdf" in cd
    assert client.get(link["url"]).status_code == 200  # همان لینک تا انقضا دوباره کار می‌کند (Range/resume)


def test_download_limit(client, admin_h, customer_h):
    _buy_digital(client, admin_h, customer_h)
    aid = client.get(f"{V}/me/library", headers=customer_h).json()[0]["access_id"]
    codes = [client.post(f"{V}/me/library/{aid}/link", headers=customer_h).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 403]


def test_download_links_cannot_be_forged_or_swapped(client, admin_h, customer_h, other_h):
    import jwt as pyjwt

    _buy_digital(client, admin_h, customer_h)
    aid = client.get(f"{V}/me/library", headers=customer_h).json()[0]["access_id"]
    assert client.post(f"{V}/me/library/{aid}/link", headers=other_h).status_code == 404  # مال دیگری
    url = client.post(f"{V}/me/library/{aid}/link", headers=customer_h).json()["url"]
    token = url.rsplit("/", 1)[1]
    assert client.get(url[:-2] + ("aa" if not url.endswith("aa") else "bb")).status_code == 404  # دستکاری
    s = get_settings()
    login_token = login(client, "cust@example.com").json()["access_token"]
    assert client.get(f"{V}/downloads/{login_token}").status_code == 404  # توکن ورود ≠ لینک دانلود
    assert client.get(f"{V}/auth/me", headers=auth(token)).status_code == 401  # لینک دانلود ≠ توکن ورود
    expired = pyjwt.encode({"sub": str(aid), "aud": "download",
                            "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, s.secret_key, algorithm="HS256")
    assert client.get(f"{V}/downloads/{expired}").status_code == 404


def test_cancelling_paid_digital_order_revokes_access_and_links(client, admin_h, customer_h, db_session):
    d, o, _ = _buy_digital(client, admin_h, customer_h)
    # سفارش دیجیتال کامل شده و دیگر قابل لغو نیست؛ برای آزمون لغو، سفارش ترکیبی می‌سازیم
    p = mk_book(client, admin_h, title="چاپی", isbn="9")
    d2 = mk_book(client, admin_h, title="دوم", book_type="both", isbn="8")
    o2 = place(client, customer_h, [{"book_id": p["id"], "item_type": "physical"}, {"book_id": d2["id"], "item_type": "digital"}])
    assert client.post(f"{A}/orders/{o2['id']}/confirm-payment", headers=admin_h).json()["status"] == "paid"
    lib = {x["title"]: x["access_id"] for x in client.get(f"{V}/me/library", headers=customer_h).json()}
    url = client.post(f"{V}/me/library/{lib['دوم']}/link", headers=customer_h).json()["url"]
    client.post(f"{A}/orders/{o2['id']}/cancel", headers=admin_h, json={"reason": "بازپرداخت"})
    assert [x["title"] for x in client.get(f"{V}/me/library", headers=customer_h).json()] == ["کیهان"]
    assert client.get(url).status_code == 404


def test_cannot_buy_owned_digital_book_twice(client, admin_h, customer_h):
    d, _, _ = _buy_digital(client, admin_h, customer_h)
    r = client.post(f"{V}/orders", headers=customer_h, json={"items": [{"book_id": d["id"], "item_type": "digital"}]})
    assert r.status_code == 409 and "already own" in r.json()["detail"]


def test_x_accel_mode_hands_file_to_nginx(client, admin_h, customer_h, monkeypatch):
    _buy_digital(client, admin_h, customer_h)
    aid = client.get(f"{V}/me/library", headers=customer_h).json()[0]["access_id"]
    url = client.post(f"{V}/me/library/{aid}/link", headers=customer_h).json()["url"]
    monkeypatch.setattr(get_settings(), "use_x_accel", True)
    r = client.get(url)
    assert r.status_code == 200 and r.content == b""
    assert r.headers["x-accel-redirect"].startswith("/_protected/digital/") and r.headers["x-accel-redirect"].endswith(".pdf")
    assert r.headers["content-type"] == "application/pdf" and "attachment" in r.headers["content-disposition"]


# ---------- کوکی + CSRF روی سفارش ----------
def test_order_with_cookie_session_requires_csrf_header(client, admin_h, make_user):
    b = mk_book(client, admin_h)
    make_user("c2@example.com")
    login(client, "c2@example.com", keep_cookie=True)
    body = {"items": [{"book_id": b["id"], "item_type": "physical"}], "shipping": SHIP}
    assert client.post(f"{V}/orders", json=body).status_code == 403
    assert client.post(f"{V}/orders", json=body, headers={"X-Requested-With": "fetch"}).status_code == 201


# ---------- همزمانی واقعی (فقط PostgreSQL) ----------
@pytest.fixture()
def real_sessions(db_session):
    """هر درخواست session و اتصال جدا می‌گیرد (برخلاف fixture عادی که یک session مشترک دارد)."""
    engine = db_session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("concurrency test needs PostgreSQL row locking")
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_concurrent_orders_never_oversell(client, admin_h, customer_h, real_sessions, db_session):
    b = mk_book(client, admin_h, stock=5)
    results: list[int] = []
    barrier = threading.Barrier(12)

    def buy():
        c = TestClient(app)
        barrier.wait()
        r = c.post(f"{V}/orders", headers=customer_h, json={"items": [{"book_id": b["id"], "item_type": "physical"}], "shipping": SHIP})
        results.append(r.status_code)

    threads = [threading.Thread(target=buy) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [201] * 5 + [409] * 7, results
    assert stock(db_session, b["id"]) == 0


def test_concurrent_multi_book_orders_do_not_deadlock(client, admin_h, customer_h, real_sessions, db_session):
    x = mk_book(client, admin_h, title="x", stock=50, isbn="1")
    y = mk_book(client, admin_h, title="y", stock=50, isbn="2")
    results: list[int] = []
    barrier = threading.Barrier(16)

    def buy(first, second):
        c = TestClient(app)
        barrier.wait()
        r = c.post(f"{V}/orders", headers=customer_h, json={"shipping": SHIP, "items": [
            {"book_id": first["id"], "item_type": "physical"}, {"book_id": second["id"], "item_type": "physical"}]})
        results.append(r.status_code)

    threads = [threading.Thread(target=buy, args=(x, y) if i % 2 else (y, x)) for i in range(16)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [201] * 16, results
    assert stock(db_session, x["id"]) == 34 and stock(db_session, y["id"]) == 34
