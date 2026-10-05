from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin.router import router as admin_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.services.storage import covers_dir

settings = get_settings()

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/admin")

# فقط کاورها عمومی‌اند. فایل‌های دیجیتال هرگز mount نمی‌شوند.
app.mount("/media/covers", StaticFiles(directory=covers_dir()), name="covers")
