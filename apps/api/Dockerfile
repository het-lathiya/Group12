# Production API image (IMP-112, IMP-218; A1 §4.3, §4.5, IMD-38, IMD-103).
# Build from the repository root: docker build -f apps/api/Dockerfile --build-arg BUILD_VERSION=<sha> .
# The root .dockerignore keeps env files, virtual environments and dependencies out of the context.
# The image holds no tests and no dev extras. It holds the migrations, scripts/release.sh and
# data/ for the release task only: the container never migrates on start (IMD-38).

FROM python:3.12-slim AS build
WORKDIR /src
COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
# A wheel, not an editable install, so the prompt templates ship as package data (IMP-111).
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
COPY --from=build /wheels /wheels
RUN pip install /wheels/*.whl && rm -rf /wheels \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
# The working directory holds no app/, so `app` resolves to the installed package.
WORKDIR /srv/api
COPY apps/api/alembic.ini ./
COPY apps/api/migrations ./migrations
COPY apps/api/scripts ./scripts
# app.places.seed writes quality_report.md into each destination directory.
COPY --chown=app:app data ./data
# app.db.auth_stub looks for migrations/ beside the package directory (AUTH_STUB_SQL in app/db/reset.py).
RUN ln -s /srv/api/migrations "$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')/migrations"
USER app
EXPOSE 8000
# Last, so that a new commit reuses every layer above. /health reports it; locally it stays "dev".
ARG BUILD_VERSION=dev
ENV BUILD_VERSION=$BUILD_VERSION
# The service template sets PORT. exec makes uvicorn PID 1, so it receives SIGTERM.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
