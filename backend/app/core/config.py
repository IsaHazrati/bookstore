from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

# مقادیری که در .env.example آمده‌اند و هرگز نباید در production استفاده شوند
_PLACEHOLDERS = {"change-me", "changeme", "secret", "password"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "Bookstore API"

    # دیتابیس: یا DATABASE_URL کامل (برای تست/توسعه)، یا اجزای جدا (در docker-compose).
    # اجزای جدا امن‌ترند: رمزی که @ / : # % دارد درست escape می‌شود.
    database_url: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str | None = None

    secret_key: str
    # لیست origin های مجاز، جدا شده با کاما
    cors_origins: str = ""

    jwt_algorithm: str = "HS256"
    # توکن ادمین عمداً کوتاه‌عمرتر است
    customer_token_minutes: int = 60 * 24
    admin_token_minutes: int = 15
    # کوکی نشست مشتری در فروشگاه (HttpOnly). روی HTTP ساده (فقط توسعه) می‌شود false کرد.
    cookie_secure: bool = True
    # حداکثر تعداد هش رمز همزمان (هر هش ~۱۹MB حافظه)
    password_hash_concurrency: int = 4

    # فروش و پرداخت دستی (کارت‌به‌کارت) تا وقتی درگاه اضافه شود. همه‌ی مبالغ به ریال.
    shipping_fee_rial: int = 0
    payment_card_number: str = ""
    payment_card_holder: str = ""
    order_payment_hours: int = 48  # مهلت پرداخت؛ بعد از آن سفارش لغو و موجودی آزاد می‌شود
    max_item_quantity: int = 10
    max_downloads_per_book: int = 10
    download_link_minutes: int = 5
    # true در docker-compose: nginx خودش فایل دیجیتال را از volume سرو می‌کند (X-Accel-Redirect)
    use_x_accel: bool = False

    # آپلودها: covers/ عمومی (از /media/covers سرو می‌شود)، digital/ هرگز عمومی نیست
    upload_dir: str = "/data/uploads"
    max_cover_bytes: int = 5 * 1024 * 1024
    max_digital_bytes: int = 100 * 1024 * 1024

    @field_validator("secret_key")
    @classmethod
    def strong_secret(cls, v: str) -> str:
        if v.strip().lower() in _PLACEHOLDERS or len(v) < 32:
            raise ValueError(
                "SECRET_KEY is missing, a placeholder, or shorter than 32 characters; "
                "generate one with: openssl rand -hex 32"
            )
        return v

    @model_validator(mode="after")
    def check_database(self) -> "Settings":
        if not self.database_url and not (self.postgres_user and self.postgres_password and self.postgres_db):
            raise ValueError("set DATABASE_URL, or POSTGRES_USER + POSTGRES_PASSWORD + POSTGRES_DB")
        if (self.db_url.password or "").strip().lower() in _PLACEHOLDERS:
            raise ValueError("the database password is a placeholder; set a real POSTGRES_PASSWORD")
        return self

    @property
    def db_url(self) -> URL:
        if self.database_url:
            return make_url(self.database_url)
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
