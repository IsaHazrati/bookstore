"""ذخیره‌ی امن فایل‌های آپلودی.

- نام فایل روی دیسک همیشه تصادفی است (نام کاربر هرگز در مسیر استفاده نمی‌شود).
- نوع فایل هم با پسوند و هم با magic bytes بررسی می‌شود، نه Content-Type کلاینت.
- حجم در حین نوشتن محدود می‌شود و فایل ناقص در صورت تجاوز پاک می‌شود.
"""
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

CHUNK = 1024 * 1024

# پسوند -> تابع بررسی ۱۶ بایت اول فایل
_COVER_SIGNATURES = {
    ".jpg": lambda h: h.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda h: h.startswith(b"\xff\xd8\xff"),
    ".png": lambda h: h.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda h: h[:4] == b"RIFF" and h[8:12] == b"WEBP",
}
_DIGITAL_SIGNATURES = {
    ".pdf": lambda h: h.startswith(b"%PDF-"),
    ".epub": lambda h: h.startswith(b"PK\x03\x04"),
}


def covers_dir() -> Path:
    p = Path(get_settings().upload_dir) / "covers"
    p.mkdir(parents=True, exist_ok=True)
    return p


def digital_dir() -> Path:
    p = Path(get_settings().upload_dir) / "digital"
    p.mkdir(parents=True, exist_ok=True)
    return p


async def _save(file: UploadFile, dest_dir: Path, signatures: dict, max_bytes: int, kind: str) -> str:
    ext = Path(file.filename or "").suffix.lower()
    check = signatures.get(ext)
    if check is None:
        raise HTTPException(422, f"{kind}: unsupported file type (allowed: {', '.join(sorted(signatures))})")

    name = f"{secrets.token_hex(16)}{ext}"
    dest = dest_dir / name
    size = 0
    try:
        with dest.open("wb") as out:
            first = True
            while chunk := await file.read(CHUNK):
                if first:
                    if not check(chunk[:16]):
                        raise HTTPException(422, f"{kind}: file content does not match its extension")
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"{kind}: file too large (max {max_bytes // (1024 * 1024)} MB)")
                out.write(chunk)
            if first:
                raise HTTPException(422, f"{kind}: empty file")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return name


async def save_cover(file: UploadFile) -> str:
    """نام فایل ذخیره‌شده را برمی‌گرداند (داخل covers/)."""
    return await _save(file, covers_dir(), _COVER_SIGNATURES, get_settings().max_cover_bytes, "cover")


async def save_digital(file: UploadFile) -> str:
    """نام فایل ذخیره‌شده را برمی‌گرداند (داخل digital/)."""
    return await _save(file, digital_dir(), _DIGITAL_SIGNATURES, get_settings().max_digital_bytes, "digital file")


def delete_cover(name: str | None) -> None:
    if name:
        (covers_dir() / Path(name).name).unlink(missing_ok=True)


def delete_digital(name: str | None) -> None:
    if name:
        (digital_dir() / Path(name).name).unlink(missing_ok=True)
