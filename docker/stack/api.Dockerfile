# api: FastAPI + Alembic. Also runs the backend tests (`make test`) and the seed (`make seed`).
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data \
    PYTHONPATH=/app:/app/bot

WORKDIR /app
COPY backend/pyproject.toml ./
# Dependencies straight from pyproject.toml (runtime + dev, for `make test`).
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; open('/tmp/requirements.txt', 'w').write('\n'.join(p['dependencies'] + p['optional-dependencies']['dev']))" \
 && pip install -r /tmp/requirements.txt

RUN useradd --create-home --uid 1000 applier && mkdir -p /data && chown applier:applier /data
COPY --chown=applier:applier backend/ ./
USER applier

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
