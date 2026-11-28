"""API-01 GET /health, the 404 envelope and CORS (IMP-103; TC-288, TC-044, TC-351).

API-02 GET /health/ready against the migrated test database and a closed port (IMP-201; TC-289).
Provider status in readiness (IMP-302; FR-044: TC-006, TC-044, TC-167, TC-168).
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fixtures.auth import AuthUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderAuthError
from app.ai.factory import get_provider
from app.ai.providers.mock import MockProvider
from app.core import health
from app.core.config import Settings
from app.db.models import AiGeneration, Destination
from app.main import create_app
from app.places import seed
from app.schemas.ai import GenerationRequest, HealthStatus

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"
CLOSED_PORT_URL = "postgresql+psycopg://ready-user:ready-db-secret@127.0.0.1:9/nowhere"

ALLOWED_ORIGIN = "http://localhost:3000"
# Fake values: the test asserts that none of them is returned.
SECRETS = {
    "database_url": "postgresql+psycopg://health-user:health-db-secret@db.invalid/app",
    "gemini_api_key": "health-test-gemini-key-not-real",
    "supabase_jwt_secret": "health-test-jwt-secret-not-real",
    "ors_api_key": "health-test-ors-key-not-real",
}


@pytest.fixture
def client(clean_settings_env: pytest.MonkeyPatch) -> TestClient:
    settings = Settings(
        app_env="test",
        ai_provider="MOCK",
        build_version="test-build",
        allowed_origins=[ALLOWED_ORIGIN],
        **SECRETS,
    )
    return TestClient(create_app(settings))


# TC-288, TC-044: 200 with exactly the four fields and no secret.
def test_health_returns_status_version_environment_provider(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "test-build",
        "environment": "test",
        "provider": "MOCK",
    }
    for secret in SECRETS.values():
        assert secret not in response.text
        assert all(secret not in value for value in response.headers.values())


def test_health_is_outside_api_v1(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 404


def test_health_has_a_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_health_echoes_a_client_request_id(client: TestClient) -> None:
    request_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] == request_id


def test_health_replaces_a_request_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "not-a-uuid"})
    assert response.headers["X-Request-ID"] != "not-a-uuid"
    assert uuid.UUID(response.headers["X-Request-ID"])


# Card step 7: an unknown route returns the 404 envelope with the request ID.
def test_health_unknown_route_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/no-such-route")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["details"] == []
    assert body["error"]["retry_after_s"] is None
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert uuid.UUID(body["error"]["request_id"])


def test_health_unknown_api_v1_route_returns_not_found_envelope(client: TestClient) -> None:
    request_id = str(uuid.uuid4())
    response = client.get("/api/v1/no-such-route", headers={"X-Request-ID": request_id})
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == request_id


# TC-351: only the exact configured origin gets a CORS allow header.
def test_health_cors_allows_the_configured_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


@pytest.mark.parametrize(
    "origin",
    ["https://evil.example", "http://localhost:3001", "http://localhost:3000.evil.example"],
)
def test_health_cors_refuses_other_origins(client: TestClient, origin: str) -> None:
    response = client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

    preflight = client.options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_health_docs_are_served_outside_production(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


def test_health_docs_are_disabled_in_production(clean_settings_env: pytest.MonkeyPatch) -> None:
    settings = Settings(
        app_env="production",
        ai_provider="GEMINI",
        gemini_api_key="health-test-gemini-key-not-real",
        gemini_model_id="test-model-id",
        gemini_embedding_model_id="gemini-embedding-2",
        database_url=SECRETS["database_url"],
    )
    production = TestClient(create_app(settings))
    assert production.get("/docs").status_code == 404
    assert production.get("/openapi.json").status_code == 404
    assert production.get("/health").json()["environment"] == "production"


# ---------- API-02 GET /health/ready (IMP-201) ----------


def ready_client(database_url: str, **overrides: Any) -> TestClient:
    values: dict[str, Any] = {
        "app_env": "test",
        "ai_provider": "MOCK",
        "build_version": "test-build",
        "database_url": database_url,
        **overrides,
    }
    return TestClient(create_app(Settings(**values)))


def test_health_ready_migration_head_matches_the_migrations() -> None:
    # The image has no migrations folder, so the head is a constant; a new migration updates it.
    head = ScriptDirectory(str(MIGRATIONS)).get_current_head()
    assert head == health.MIGRATION_HEAD


def test_health_ready_with_a_migrated_database(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url)
    response = client.get("/health/ready")
    assert response.status_code == 200
    model_id = get_provider(client.app.state.settings).get_model_metadata().model_id
    head = ScriptDirectory(str(MIGRATIONS)).get_current_head()
    assert response.json() == {
        "status": "ready",
        "version": "test-build",
        "checks": {
            "database": "ok",
            "migration": head,
            "provider": {"name": "MOCK", "model_id": model_id, "status": "ok"},
        },
    }


# TC-289: the database unreachable -> 503 not_ready naming the database; no secret in the body.
def test_health_ready_database_down_is_503_not_ready(
    clean_settings_env: pytest.MonkeyPatch,
) -> None:
    response = ready_client(CLOSED_PORT_URL).get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "down"
    assert body["checks"]["migration"] == "behind"
    assert body["checks"]["provider"]["status"] == "ok"
    assert "ready-db-secret" not in response.text
    assert "127.0.0.1" not in response.text


# PD-12, FR-044 AC2: a provider that is down degrades readiness but is not a 503.
def test_health_ready_provider_down_is_200_degraded(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url, ai_provider="GEMINI", gemini_model_id="m-test")
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["provider"] == {"name": "GEMINI", "model_id": "m-test", "status": "down"}


def test_health_ready_database_behind_the_head_is_degraded(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    clean_settings_env.setattr(health, "MIGRATION_HEAD", "9999")
    response = ready_client(migrated_database_url).get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["migration"] == "behind"


def test_health_ready_caches_the_provider_check(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url)
    provider = get_provider(client.app.state.settings)
    calls = []

    async def counting_health_check() -> HealthStatus:
        calls.append(1)
        return HealthStatus(status="ok", detail=None, checked_at=datetime.now(UTC))

    clean_settings_env.setattr(provider, "health_check", counting_health_check)
    client.app.state.model_provider = provider
    for _ in range(3):
        assert client.get("/health/ready").status_code == 200
    assert len(calls) == 1  # cached for PROVIDER_CACHE_S


def test_health_ready_checks_the_provider_again_after_the_cache_expires(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url)
    provider = MockProvider("ok", app_env="test")
    client.app.state.model_provider = provider
    clock = [1000.0]
    clean_settings_env.setattr(health.time, "monotonic", lambda: clock[0])

    assert client.get("/health/ready").json()["status"] == "ready"
    provider.raise_error = ProviderAuthError()
    clock[0] += health.PROVIDER_CACHE_S - 1
    assert client.get("/health/ready").json()["status"] == "ready"  # still the cached answer
    clock[0] += 1
    assert client.get("/health/ready").json()["status"] == "degraded"


# ---------- Provider status (IMP-302; FR-044) ----------


class CountingProvider(MockProvider):
    """Counts health checks and refuses any generation."""

    def __init__(self) -> None:
        super().__init__("ok", app_env="test")
        self.health_checks = 0

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        raise AssertionError("a health route called the model")

    async def health_check(self) -> HealthStatus:
        self.health_checks += 1
        return await super().health_check()


# TC-167: FR-044 AC1.
def test_tc_167_health_ready_names_the_provider_model_and_status(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url)
    client.app.state.model_provider = MockProvider("ok", app_env="test")

    check = client.get("/health/ready").json()["checks"]["provider"]

    assert check == {"name": "MOCK", "model_id": "mock-v1", "status": "ok"}


# API-01 names the provider and calls nothing; TC-006 covers the readiness side.
def test_tc_167_health_gives_the_provider_name_with_no_provider_call(client: TestClient) -> None:
    provider = CountingProvider()
    client.app.state.model_provider = provider

    assert client.get("/health").json()["provider"] == "MOCK"
    assert provider.health_checks == 0


# TC-168: FR-044 AC2, with MOCK raising the auth error (IMD-27) and with GEMINI without a key.
def test_tc_168_mock_auth_error_is_200_degraded_with_the_provider_down(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url)
    client.app.state.model_provider = MockProvider(
        "ok", app_env="test", raise_error=ProviderAuthError()
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["provider"] == {"name": "MOCK", "model_id": "mock-v1", "status": "down"}


def test_tc_168_gemini_without_a_key_is_200_degraded(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    client = ready_client(migrated_database_url, ai_provider="GEMINI", gemini_model_id="m-test")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["provider"]["status"] == "down"


@pytest.mark.parametrize("status", ["degraded", "down"])
def test_tc_168_only_the_database_makes_readiness_503(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str, status: Any
) -> None:
    class Unwell(MockProvider):
        async def health_check(self) -> HealthStatus:
            return HealthStatus(status=status, detail=None, checked_at=datetime.now(UTC))

    client = ready_client(migrated_database_url)
    client.app.state.model_provider = Unwell("ok", app_env="test")

    response = client.get("/health/ready")

    assert (response.status_code, response.json()["status"]) == (200, "degraded")
    assert response.json()["checks"]["provider"]["status"] == status


@pytest.mark.asyncio
async def test_tc_168_with_the_provider_down_non_ai_routes_still_answer(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
) -> None:
    api_app.state.model_provider = MockProvider(
        "ok", app_env="test", raise_error=ProviderAuthError()
    )
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    created = await api_client.post(
        "/api/v1/trips",
        json={
            "title": "Weekend in Sampleton",
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-06",
            "adults": 2,
        },
        headers=auth_user.headers,
    )
    assert created.status_code == 201, created.text

    listed = await api_client.get("/api/v1/trips", headers=auth_user.headers)
    read = await api_client.get(f"/api/v1/trips/{created.json()['id']}", headers=auth_user.headers)

    assert listed.status_code == 200, listed.text  # API-08
    assert read.status_code == 200, read.text  # API-10


# TC-044: the fields are an allow-list, so a detail holding a secret goes nowhere.
def test_tc_044_health_ready_returns_no_provider_detail(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    leak = "key=health-test-gemini-key-not-real&prompt=A%20private%20note"

    class Leaky(MockProvider):
        async def health_check(self) -> HealthStatus:
            return HealthStatus(status="down", detail=leak, checked_at=datetime.now(UTC))

    client = ready_client(migrated_database_url)
    client.app.state.model_provider = Leaky("ok", app_env="test")

    response = client.get("/health/ready")

    assert set(response.json()["checks"]["provider"]) == {"name", "model_id", "status"}
    assert leak not in response.text
    assert "health-test-gemini-key-not-real" not in response.text


def test_tc_044_health_ready_shows_no_gemini_key(
    clean_settings_env: pytest.MonkeyPatch, migrated_database_url: str
) -> None:
    key = SECRETS["gemini_api_key"]
    client = ready_client(
        migrated_database_url, ai_provider="GEMINI", gemini_api_key=key, gemini_model_id="m-test"
    )

    response = client.get("/health/ready")

    assert response.json()["checks"]["provider"]["status"] == "ok"
    assert key not in response.text


# TC-006: readiness makes no generation call and writes no generation row.
@pytest.mark.asyncio
async def test_tc_006_health_ready_makes_no_generation_call_and_no_row(
    api_app: FastAPI, api_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    provider = CountingProvider()
    api_app.state.model_provider = provider
    count = select(func.count()).select_from(AiGeneration)
    before = await db_session.scalar(count)

    await api_client.get("/health/ready")

    assert provider.health_checks == 1
    assert await db_session.scalar(count) == before


# TC-342: readiness answers carry the request ID, and a client UUID is echoed.
def test_health_ready_echoes_a_client_request_id(clean_settings_env: pytest.MonkeyPatch) -> None:
    request_id = str(uuid.uuid4())
    response = ready_client(CLOSED_PORT_URL).get(
        "/health/ready", headers={"X-Request-ID": request_id}
    )
    assert response.headers["X-Request-ID"] == request_id
