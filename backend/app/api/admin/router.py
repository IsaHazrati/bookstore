from fastapi import APIRouter, Depends

from app.api.admin.catalog import router as catalog_router
from app.api.admin.orders import router as orders_router
from app.api.deps.auth import require_admin

# همه‌ی endpoint های این روتر فقط برای نقش admin باز است
router = APIRouter(dependencies=[Depends(require_admin)])

router.include_router(catalog_router)
router.include_router(orders_router)


@router.get("/ping", tags=["admin"])
def ping() -> dict[str, str]:
    return {"scope": "admin"}
