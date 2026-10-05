from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models.enums import ItemType
from app.models.order import Order, OrderItem

A = "/api/admin"
V = "/api/v1"

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


def mk_book(client, h, **over):
    body = {"title": "بوف کور", "author": "صادق هدایت", "book_type": "physical", "price": 120000, "stock_quantity": 5,
            "is_published": True}
    body.update(over)
    r = client.post(f"{A}/books", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def mk_cat(client, h, name="رمان"):
    r = client.post(f"{A}/categories", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- دسترسی ----------
@pytest.mark.parametrize("method,path", [("get", "/books"), ("post", "/books"), ("get", "/categories"), ("post", "/categories")])
def test_admin_catalog_needs_admin(client, customer_h, method, path):
    assert getattr(client, method)(A + path).status_code == 401
    assert getattr(client, method)(A + path, headers=customer_h).status_code == 403


# ---------- دسته‌بندی ----------
def test_category_crud_and_persian_slug(client, admin_h):
    c = mk_cat(client, admin_h, "علمی تخیلی")
    assert c["slug"] == "علمی-تخیلی"
    assert client.post(f"{A}/categories", json={"name": "علمی تخیلی"}, headers=admin_h).status_code == 409
    r = client.put(f"{A}/categories/{c['id']}", json={"name": "علمی"}, headers=admin_h)
    assert r.status_code == 200 and r.json()["name"] == "علمی"
    assert client.delete(f"{A}/categories/{c['id']}", headers=admin_h).status_code == 204
    assert client.delete(f"{A}/categories/{c['id']}", headers=admin_h).status_code == 404


def test_category_with_books_cannot_be_deleted(client, admin_h):
    c = mk_cat(client, admin_h)
    mk_book(client, admin_h, category_id=c["id"])
    assert client.delete(f"{A}/categories/{c['id']}", headers=admin_h).status_code == 409


# ---------- کتاب ----------
def test_book_slug_auto_and_dedup(client, admin_h):
    b1 = mk_book(client, admin_h, isbn="111")
    b2 = mk_book(client, admin_h, isbn="222")
    assert b1["slug"] == "بوف-کور" and b2["slug"] == "بوف-کور-2"
    r = client.post(f"{A}/books", headers=admin_h,
                    json={"title": "x", "author": "y", "book_type": "physical", "price": 1, "isbn": "111"})
    assert r.status_code == 409


def test_book_validation(client, admin_h):
    base = {"title": "t", "author": "a", "book_type": "physical", "price": 1}
    for bad in ({"price": -1}, {"stock_quantity": -1}, {"title": "  "}, {"book_type": "audio"}, {"category_id": 999}):
        r = client.post(f"{A}/books", json={**base, **bad}, headers=admin_h)
        assert r.status_code == 422, bad


def test_digital_book_needs_file_before_publish(client, admin_h):
    r = client.post(f"{A}/books", headers=admin_h,
                    json={"title": "d", "author": "a", "book_type": "digital", "price": 1, "is_published": True})
    assert r.status_code == 422
    b = mk_book(client, admin_h, title="d", book_type="digital", is_published=False, stock_quantity=9)
    assert b["stock_quantity"] == 0  # موجودی برای دیجیتال صفر می‌شود
    up = client.post(f"{A}/books/{b['id']}/digital-file", headers=admin_h, files={"file": ("a.pdf", PDF)})
    assert up.status_code == 200 and up.json()["has_digital_file"] is True
    pub = client.put(f"{A}/books/{b['id']}", headers=admin_h,
                     json={"title": "d", "author": "a", "book_type": "digital", "price": 1, "is_published": True})
    assert pub.status_code == 200 and pub.json()["is_published"] is True


def test_cannot_make_book_physical_while_it_has_digital_file(client, admin_h):
    b = mk_book(client, admin_h, book_type="both", is_published=False)
    client.post(f"{A}/books/{b['id']}/digital-file", headers=admin_h, files={"file": ("a.pdf", PDF)})
    r = client.put(f"{A}/books/{b['id']}", headers=admin_h,
                   json={"title": "t", "author": "a", "book_type": "physical", "price": 1})
    assert r.status_code == 422


def test_physical_book_rejects_digital_upload(client, admin_h):
    b = mk_book(client, admin_h)
    r = client.post(f"{A}/books/{b['id']}/digital-file", headers=admin_h, files={"file": ("a.pdf", PDF)})
    assert r.status_code == 422


def test_delete_book_blocked_when_ordered(client, admin_h, db_session, make_user):
    b = mk_book(client, admin_h)
    u = make_user("buyer@example.com")
    o = Order(user_id=u.id)
    o.items.append(OrderItem(book_id=b["id"], item_type=ItemType.physical, quantity=1, unit_price=1))
    db_session.add(o)
    db_session.commit()
    assert client.delete(f"{A}/books/{b['id']}", headers=admin_h).status_code == 409


# ---------- آپلود ----------
def test_cover_upload_serves_and_replaces(client, admin_h):
    b = mk_book(client, admin_h)
    r1 = client.post(f"{A}/books/{b['id']}/cover", headers=admin_h, files={"file": ("c.jpg", JPEG)})
    url1 = r1.json()["cover_image_url"]
    assert r1.status_code == 200 and url1.startswith("/media/covers/") and url1.endswith(".jpg")
    assert client.get(url1).content == JPEG
    r2 = client.post(f"{A}/books/{b['id']}/cover", headers=admin_h, files={"file": ("c2.jpg", JPEG + b"1")})
    assert client.get(url1).status_code == 404  # کاور قبلی پاک شده
    assert client.get(r2.json()["cover_image_url"]).status_code == 200


@pytest.mark.parametrize(
    "kind,name,content,code",
    [
        ("cover", "x.exe", b"MZ" + b"0" * 30, 422),
        ("cover", "x.jpg", b"not really a jpeg at all", 422),   # پسوند درست، محتوای اشتباه
        ("cover", "x.jpg", b"", 422),
        ("digital-file", "x.pdf", b"<html>evil</html>", 422),
        ("digital-file", "x.html", PDF, 422),
    ],
)
def test_upload_rejections(client, admin_h, kind, name, content, code):
    b = mk_book(client, admin_h, book_type="both", is_published=False)
    r = client.post(f"{A}/books/{b['id']}/{kind}", headers=admin_h, files={"file": (name, content)})
    assert r.status_code == code


def test_upload_size_limit_and_no_leftover_file(client, admin_h, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_cover_bytes", 10)
    b = mk_book(client, admin_h)
    before = set(Path(get_settings().upload_dir, "covers").iterdir())
    r = client.post(f"{A}/books/{b['id']}/cover", headers=admin_h, files={"file": ("c.jpg", JPEG)})
    assert r.status_code == 413
    assert set(Path(get_settings().upload_dir, "covers").iterdir()) == before


def test_upload_filename_cannot_escape_directory(client, admin_h):
    b = mk_book(client, admin_h)
    r = client.post(f"{A}/books/{b['id']}/cover", headers=admin_h, files={"file": ("../../evil.jpg", JPEG)})
    assert r.status_code == 200
    assert "evil" not in r.json()["cover_image_url"]


def test_digital_files_are_never_public(client, admin_h):
    b = mk_book(client, admin_h, book_type="both", is_published=False)
    client.post(f"{A}/books/{b['id']}/digital-file", headers=admin_h, files={"file": ("secret.pdf", PDF)})
    client.put(f"{A}/books/{b['id']}", headers=admin_h,
               json={"title": "t", "author": "a", "book_type": "both", "price": 1, "is_published": True})
    digital = Path(get_settings().upload_dir, "digital")
    stored = next(digital.iterdir()).name
    slug = client.get(f"{A}/books/{b['id']}", headers=admin_h).json()["slug"]
    pub = client.get(f"{V}/books/{slug}")
    assert pub.status_code == 200
    assert stored not in pub.text and "digital_file" not in pub.text and pub.json()["has_digital"] is True
    for url in (f"/media/digital/{stored}", f"/media/covers/{stored}", f"/media/covers/../digital/{stored}"):
        assert client.get(url).status_code == 404


# ---------- کاتالوگ عمومی ----------
def test_public_catalog_listing_filters_and_paging(client, admin_h):
    novel = mk_cat(client, admin_h, "رمان")
    sci = mk_cat(client, admin_h, "علمی")
    mk_book(client, admin_h, title="بوف کور", author="هدایت", price=100, category_id=novel["id"], isbn="1")
    mk_book(client, admin_h, title="کلیدر", author="دولت‌آبادی", price=300, category_id=novel["id"], isbn="2",
            book_type="both", is_published=False)
    mk_book(client, admin_h, title="کیهان", author="ساگان", price=200, category_id=sci["id"], isbn="3")
    mk_book(client, admin_h, title="خانه ارواح", author="آلنده", price=50, isbn="4")

    allb = client.get(f"{V}/books").json()
    assert allb["total"] == 3 and all(b["title"] != "کلیدر" for b in allb["items"])  # منتشرنشده پنهان است

    assert [b["title"] for b in client.get(f"{V}/books", params={"category": "رمان"}).json()["items"]] == ["بوف کور"]
    assert client.get(f"{V}/books", params={"q": "ساگان"}).json()["total"] == 1
    assert client.get(f"{V}/books", params={"q": "%"}).json()["total"] == 0  # wildcard هرز escape می‌شود
    prices = [b["price"] for b in client.get(f"{V}/books", params={"sort": "price_asc"}).json()["items"]]
    assert [float(p) for p in prices] == [50, 100, 200]
    p2 = client.get(f"{V}/books", params={"page": 2, "page_size": 2}).json()
    assert p2["total"] == 3 and len(p2["items"]) == 1
    assert client.get(f"{V}/books", params={"page_size": 1000}).status_code == 422


def test_public_type_filter_includes_both(client, admin_h):
    mk_book(client, admin_h, title="p", isbn="1")
    b = mk_book(client, admin_h, title="b", book_type="both", is_published=False, isbn="2")
    client.post(f"{A}/books/{b['id']}/digital-file", headers=admin_h, files={"file": ("a.pdf", PDF)})
    client.put(f"{A}/books/{b['id']}", headers=admin_h,
               json={"title": "b", "author": "a", "book_type": "both", "price": 1, "is_published": True})
    titles = lambda t: sorted(x["title"] for x in client.get(f"{V}/books", params={"book_type": t}).json()["items"])
    assert titles("physical") == ["b", "p"]
    assert titles("digital") == ["b"]


def test_public_book_detail_and_hidden_unpublished(client, admin_h):
    b = mk_book(client, admin_h, stock_quantity=0)
    r = client.get(f"{V}/books/{b['slug']}")
    assert r.status_code == 200 and r.json()["in_stock"] is False
    client.put(f"{A}/books/{b['id']}", headers=admin_h,
               json={"title": "بوف کور", "author": "a", "book_type": "physical", "price": 1, "is_published": False})
    assert client.get(f"{V}/books/{b['slug']}").status_code == 404
    assert client.get(f"{V}/books/nope").status_code == 404


# ---------- یکسان‌سازی فارسی و slug ----------
def test_persian_search_matches_keyboard_and_spacing_variants(client, admin_h):
    mk_book(client, admin_h, title="علي و كتابهای خوب", author="نويسنده", isbn="1")  # با کیبورد عربی
    mk_book(client, admin_h, title="۱۹۸۴", author="جورج اورول", isbn="2")
    def total(q):
        return client.get(f"{V}/books", params={"q": q}).json()["total"]
    assert total("علی") == 1 and total("علي") == 1
    assert total("کتاب‌های") == 1 and total("کتاب های") == 1 and total("کتابهای") == 1
    assert total("نویسنده") == 1
    assert total("1984") == 1 and total("۱۹۸۴") == 1
    assert total("%") == 0 and total("___") == 0
    # پنل ادمین هم همین جستجو را دارد
    assert client.get(f"{A}/books", params={"q": "علی"}, headers=admin_h).json()["total"] == 1


def test_search_text_follows_title_changes(client, admin_h):
    b = mk_book(client, admin_h, title="قدیمی", isbn="1")
    client.put(f"{A}/books/{b['id']}", headers=admin_h,
               json={"title": "جدید", "author": "a", "book_type": "physical", "price": 1, "is_published": True})
    assert client.get(f"{V}/books", params={"q": "جدید"}).json()["total"] == 1
    assert client.get(f"{V}/books", params={"q": "قدیمی"}).json()["total"] == 0


def test_long_duplicate_slugs_do_not_overflow(client, admin_h):
    long_cat = "ا" * 140
    c1 = client.post(f"{A}/categories", json={"name": "c1", "slug": long_cat}, headers=admin_h)
    c2 = client.post(f"{A}/categories", json={"name": "c2", "slug": long_cat}, headers=admin_h)
    assert c1.status_code == c2.status_code == 201
    assert c2.json()["slug"].endswith("-2") and len(c2.json()["slug"]) <= 140
    body = {"title": "t", "author": "a", "book_type": "physical", "price": 1, "slug": "b" * 280}
    b1 = client.post(f"{A}/books", json=body, headers=admin_h)
    b2 = client.post(f"{A}/books", json={**body, "isbn": None}, headers=admin_h)
    assert b1.status_code == b2.status_code == 201
    assert b2.json()["slug"].endswith("-2") and len(b2.json()["slug"]) <= 280


def test_slug_without_diacritics(client, admin_h):
    b = mk_book(client, admin_h, title="کِتابِ مُقَدّس")
    assert b["slug"] == "کتاب-مقدس"


def test_new_book_defaults_to_draft(client, admin_h):
    r = client.post(f"{A}/books", headers=admin_h, json={"title": "t", "author": "a", "book_type": "physical", "price": 1})
    assert r.status_code == 201 and r.json()["is_published"] is False
    assert client.get(f"{V}/books/{r.json()['slug']}").status_code == 404
