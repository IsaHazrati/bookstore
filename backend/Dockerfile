FROM python:3.12-slim

# MALLOC_ARENA_MAX=2: بدون آن، glibc حافظه‌ی آزادشده‌ی هش‌های Argon2 را در arenaهای هر thread نگه
# می‌داشت و RSS با هر موج درخواست ورود بالا می‌رفت (اندازه‌گیری‌شده: ۵۴۲→۶۷۶MB در برابر ~۲۴۰MB ثابت)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN useradd --create-home appuser \
 && mkdir -p /data/uploads \
 && chown -R appuser:appuser /data
ENV UPLOAD_DIR=/data/uploads
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
