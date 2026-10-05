from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "Bookstore API"
    database_url: str
    secret_key: str
    # لیست origin های مجاز، جدا شده با کاما
    cors_origins: str = ""

    jwt_algorithm: str = "HS256"
    # توکن ادمین عمداً کوتاه‌عمرتر است
    customer_token_minutes: int = 60 * 24
    admin_token_minutes: int = 15

    # آپلودها: covers/ عمومی (از /media/covers سرو می‌شود)، digital/ هرگز عمومی نیست
    upload_dir: str = "/data/uploads"
    max_cover_bytes: int = 5 * 1024 * 1024
    max_digital_bytes: int = 100 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
