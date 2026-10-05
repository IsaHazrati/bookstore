import pytest

from app.core.slug import slugify
from app.core.text import search_key


@pytest.mark.parametrize("a,b", [
    ("علي", "علی"),            # ی عربی/فارسی
    ("كتاب", "کتاب"),          # ک عربی/فارسی
    ("کتاب‌ها", "کتابها"),      # نیم‌فاصله
    ("کتاب ها", "کتابها"),      # فاصله
    ("کِتابِ مُقَدَّس", "کتاب مقدس"),  # اعراب
    ("کتـــاب", "کتاب"),        # کشیده
    ("۱۹۸۴", "1984"), ("١٩٨٤", "1984"),  # ارقام
    ("آبی", "ابی"), ("خانۀ ما", "خانه ما"),
    ("Hello World", "helloworld"),
])
def test_search_key_unifies_variants(a, b):
    assert search_key(a) == search_key(b)


def test_search_key_strips_like_wildcards():
    assert search_key("%_%") == ""


def test_slug_drops_diacritics_and_unifies_letters():
    assert slugify("کِتابِ مُقَدّس") == "کتاب-مقدس"
    assert slugify("علي و كتاب") == slugify("علی و کتاب") == "علی-و-کتاب"
    assert slugify("کتاب‌ها") == "کتاب-ها"


def test_slug_max_len():
    assert len(slugify("ا" * 300, max_len=140)) == 140
    assert slugify("---", max_len=10) == "item"
