# All for Cabal Web — production image (Render or any Docker host).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install Python deps and the headless Chromium that Playwright drives.
COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && python -m playwright install --with-deps chromium

COPY . .

# Apply migrations, then serve. Render injects $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
