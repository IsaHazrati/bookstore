import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD_KEY = "k" * 40


def make(**kw):
    base = {"secret_key": GOOD_KEY, "database_url": "sqlite://"}
    base.update(kw)
    return Settings(_env_file=None, **base)


@pytest.mark.parametrize("key", ["change-me", "short", "x" * 31, "CHANGE-ME"])
def test_weak_secret_key_is_rejected(key):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(secret_key=key)


def test_strong_secret_key_is_accepted():
    assert make().secret_key == GOOD_KEY


@pytest.mark.parametrize("pw", ["p@ss/w+rd=", "a:b#c%d?e", "ساده۱۲۳"])
def test_database_password_with_special_characters(pw):
    s = make(database_url=None, postgres_user="bookstore", postgres_password=pw, postgres_db="bookstore")
    url = s.db_url
    assert (url.host, url.password, url.database, url.port) == ("db", pw, "bookstore", 5432)
    # رفت‌وبرگشت از رشته هم سالم می‌ماند
    from sqlalchemy.engine import make_url

    again = make_url(url.render_as_string(hide_password=False))
    assert (again.host, again.password) == ("db", pw)


def test_placeholder_database_password_is_rejected():
    with pytest.raises(ValidationError, match="placeholder"):
        make(database_url=None, postgres_user="u", postgres_password="change-me", postgres_db="d")


def test_database_settings_required():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        make(database_url=None)
