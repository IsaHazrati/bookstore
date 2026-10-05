import re

from app.core.text import fa_letters

_ZWNJ = "‌"


def slugify(text: str, max_len: int | None = None) -> str:
    """slug یونیکدی: حروف فارسی/لاتین و اعداد را نگه می‌دارد، بقیه را به خط‌تیره تبدیل می‌کند."""
    text = fa_letters(text).strip().lower()
    text = text.replace(_ZWNJ, "-").replace(" ", "-")
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    if max_len:
        text = text[:max_len].rstrip("-_")
    return text or "item"
