from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.catalog import Book
from app.models.digital_access import DigitalAccess
from app.models.user import User
from app.services import downloads, storage
from app.services.orders import _aware, utcnow

router = APIRouter(tags=["library"])


class LibraryItem(BaseModel):
    access_id: int
    book_id: int
    title: str
    author: str
    slug: str
    cover_image_url: str | None
    file_format: str | None
    download_count: int
    max_downloads: int
    downloads_left: int
    expires_at: datetime | None


class DownloadLink(BaseModel):
    url: str
    expires_in: int
    downloads_left: int


@router.get("/me/library", response_model=list[LibraryItem])
def my_library(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[LibraryItem]:
    rows = db.execute(
        select(DigitalAccess, Book).join(Book, Book.id == DigitalAccess.book_id)
        .where(DigitalAccess.user_id == user.id).order_by(DigitalAccess.id.desc())
    ).all()
    return [
        LibraryItem(
            access_id=a.id, book_id=b.id, title=b.title, author=b.author, slug=b.slug,
            cover_image_url=b.cover_image_url,
            file_format=Path(b.digital_file_path).suffix.lstrip(".").upper() if b.digital_file_path else None,
            download_count=a.download_count, max_downloads=a.max_downloads,
            downloads_left=max(0, a.max_downloads - a.download_count), expires_at=a.expires_at,
        )
        for a, b in rows
    ]


@router.post("/me/library/{access_id}/link", response_model=DownloadLink)
def create_download_link(access_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DownloadLink:
    access = db.scalar(select(DigitalAccess).where(DigitalAccess.id == access_id, DigitalAccess.user_id == user.id))
    if access is None:
        raise HTTPException(404, "not found")
    if access.expires_at and _aware(access.expires_at) < utcnow():
        raise HTTPException(403, "your access to this book has expired")
    book = db.get(Book, access.book_id)
    if book is None or not book.digital_file_path:
        raise HTTPException(409, "the file is temporarily unavailable; please contact support")
    # افزایش اتمی شمارنده: دو کلیک همزمان نمی‌توانند از سقف عبور کنند
    res = db.execute(
        update(DigitalAccess)
        .where(DigitalAccess.id == access.id, DigitalAccess.download_count < DigitalAccess.max_downloads)
        .values(download_count=DigitalAccess.download_count + 1)
        .execution_options(synchronize_session=False)
    )
    if res.rowcount != 1:
        db.rollback()
        raise HTTPException(403, "download limit reached; please contact support")
    db.commit()
    db.refresh(access)
    token, seconds = downloads.make_token(access.id)
    return DownloadLink(url=f"/api/v1/downloads/{token}", expires_in=seconds,
                        downloads_left=max(0, access.max_downloads - access.download_count))


@router.get("/downloads/{token}")
def download(token: str, db: Session = Depends(get_db)) -> Response:
    access_id = downloads.read_token(token)
    if access_id is None:
        raise HTTPException(404, "this download link is invalid or has expired")
    access = db.get(DigitalAccess, access_id)  # اگر سفارش لغو شده باشد، دسترسی حذف شده است
    book = db.get(Book, access.book_id) if access else None
    if book is None or not book.digital_file_path:
        raise HTTPException(404, "this download link is invalid or has expired")
    name = Path(book.digital_file_path).name
    filename = f"{book.slug}{Path(name).suffix.lower()}"
    headers = {"Content-Disposition": downloads.content_disposition(filename), "Cache-Control": "private, no-store"}
    if get_settings().use_x_accel:
        # nginx فایل را از location داخلی /_protected/digital/ سرو می‌کند (با پشتیبانی Range)
        headers["X-Accel-Redirect"] = f"/_protected/digital/{name}"
        return Response(status_code=200, headers=headers, media_type=downloads.media_type(name))
    path = storage.digital_dir() / name
    if not path.is_file():
        raise HTTPException(404, "this download link is invalid or has expired")
    return FileResponse(path, media_type=downloads.media_type(name), headers=headers)
