FROM python:3.11-slim

# Don't write .pyc, flush stdout/stderr immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /service

# Install deps first so this layer is cached when only app changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy just the application package — .dockerignore excludes tests/data/docs.
COPY app ./app

# Run as a non-root user.
RUN groupadd --system --gid 1000 gridwise \
    && useradd  --system --uid 1000 --gid gridwise --home /service gridwise \
    && chown -R gridwise:gridwise /service
USER gridwise

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health',timeout=2).status==200 else 1)" \
    || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
