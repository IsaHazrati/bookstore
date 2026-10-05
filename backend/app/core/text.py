"""یکسان‌سازی متن فارسی برای slug و جستجو.

مشکلاتی که حل می‌کند (همه در بررسی کد دیده شد):
- «علي»/«كتاب» با کیبورد عربی ≠ «علی»/«کتاب» با کیبورد فارسی
- «کتاب‌ها» / «کتابها» / «کتاب ها» سه جستجوی متفاوت بودند
- اعراب slug را خراب می‌کرد: «کِتاب» → «ک-تاب»
"""
import re
import unicodedata

# حروف عربی → معادل فارسی (برای همه‌جا، از جمله slug)
_LETTERS = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
# یکسان‌سازی بیشتر فقط برای کلید جستجو (نه نمایش و نه slug)
_SEARCH_ONLY = str.maketrans({
    "آ": "ا", "أ": "ا", "إ": "ا", "ٱ": "ا",
    "ۀ": "ه", "ة": "ه", "ؤ": "و",
    **{chr(0x06F0 + i): str(i) for i in range(10)},  # ارقام فارسی
    **{chr(0x0660 + i): str(i) for i in range(10)},  # ارقام عربی
})
# اعراب (فتحه، کسره، تشدید، تنوین، ...)، الف کوچک بالا، علائم قرآنی، و کشیده (ـ)
_MARKS = re.compile(r"[ً-ٰٟۖ-ۭـ]")


def fa_letters(text: str) -> str:
    """یکسان‌سازی سبک: شکل‌های عربی حروف و اعراب. معنای متن عوض نمی‌شود."""
    text = unicodedata.normalize("NFKC", text)
    return _MARKS.sub("", text).translate(_LETTERS)


def search_key(text: str) -> str:
    """کلید جستجو: بدون فاصله، نیم‌فاصله، علائم و اعراب؛ حروف و ارقام یکسان‌شده."""
    text = fa_letters(text).translate(_SEARCH_ONLY).lower()
    return re.sub(r"[\W_]+", "", text)


def like_contains(key: str) -> str:
    """الگوی LIKE «شامل بودن» با escape کاراکترهای ویژه."""
    return "%" + key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


_DIGITS = str.maketrans({**{chr(0x06F0 + i): str(i) for i in range(10)}, **{chr(0x0660 + i): str(i) for i in range(10)}})


def ascii_digits(text: str) -> str:
    """۰۹۱۲ → 0912 (برای موبایل، شماره پیگیری، کد پستی)."""
    return text.translate(_DIGITS)
