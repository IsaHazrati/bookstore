"""لینک دانلود کوتاه‌عمر برای کتاب‌های دیجیتال.

لینک یک JWT با aud=download و انقضای چنددقیقه‌ای است؛ در دیتابیس ذخیره نمی‌شود.
- توکن ورود به‌عنوان لینک دانلود پذیرفته نمی‌شود و برعکس (بررسی aud).
- شمارش دانلود به‌ازای «صدور لینک» است، نه هر درخواست؛ پس ادامه‌ی دانلود (Range) سهمیه نمی‌خورد.
"""
import mimetypes
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import jwt

from app.core.config import get_settings
from app.services.orders import utcnow

AUDIENCE = "download"


def make_token(access_id: int) -> tuple[str, int]:
    s = get_settings()
    seconds = s.download_link_minutes * 60
    payload = {"sub": str(access_id), "aud": AUDIENCE, "exp": utcnow() + timedelta(seconds=seconds)}
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm), seconds


def read_token(token: str) -> int | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm], audience=AUDIENCE,
                             options={"require": ["exp", "sub", "aud"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None


def content_disposition(filename: str) -> str:
    """نام فایل فارسی طبق RFC 6266/5987، با جایگزین ASCII برای مرورگرهای قدیمی."""
    ascii_name = filename.encode("ascii", "ignore").decode() or "book"
    ascii_name = ascii_name.replace('"', "")
    if ascii_name.startswith("."):
        ascii_name = "book" + ascii_name
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".pdf": "application/pdf", ".epub": "application/epub+zip"}.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
