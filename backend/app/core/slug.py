import re
import unicodedata

_ZWNJ = "‌"


def slugify(text: str) -> str:
    """slug یونیکدی: حروف فارسی/لاتین و اعداد را نگه می‌دارد، بقیه را به خط‌تیره تبدیل می‌کند."""
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = text.replace(_ZWNJ, "-").replace(" ", "-")
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    return text or "item"
