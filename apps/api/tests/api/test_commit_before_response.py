"""PD-RUN-071c-1 / IMD-184: committed edits are visible when their response reaches the client.

The usual rolled-back session override cannot expose a commit race. These tests use the real
db_session dependency and separate request transactions in a dedicated migrated database, dropped
afterwards. Reading at the final response body makes the old teardown order fail deterministically
without a server, sleeps or retries.
"""

import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
import psycopg
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser, auth_test_settings, client_for
from fixtures.db import _apply_auth_stub_if_absent, _upgrade_head
from psycopg import sql
from sqlalchemy import event, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from starlette.types import Message, Receive, Scope, Send

from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.auth import deps
from app.db import session as database
from app.db.auth_stub import libpq_url
from app.db.models import Destination
from app.generation import jobs
from app.main import create_app
from app.places import seed

SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"


@pytest.fixture
def committed_database_url(migrated_database_url: str) -> Iterator[str]:
    """Isolate real commits from the other API tests' rolled-back fixtures."""
    url = make_url(migrated_database_url)
    name = f"commit_response_{uuid.uuid4().hex}"
    server = libpq_url(url.set(database="postgres").render_as_string(hide_password=False))
    with psycopg.connect(server, autocommit=True) as conn:
        conn.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
    try:
        scratch = url.set(database=name).render_as_string(hide_password=False)
        _apply_auth_stub_if_absent(scratch)
        _upgrade_head(scratch)
        yield scratch
    finally:
        with psycopg.connect(server, autocommit=True) as conn:
            conn.execute(
                sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(name))
            )


@dataclass(frozen=True)
class CommittedPlan:
    app: FastAPI
    user: AuthUser
    itinerary_url: str
    item_url: str
    revision: int


@pytest_asyncio.fixture
async def committed_plan(
    committed_database_url: str, clean_settings_env: pytest.MonkeyPatch
) -> AsyncIterator[CommittedPlan]:
    engine = database.create_engine(committed_database_url, poolclass=NullPool)
    sessions = database.create_sessionmaker(engine)
    clean_settings_env.setattr(database, "get_sessionmaker", lambda: sessions)
    clean_settings_env.setenv("APP_ENV", "test")
    app = create_app(auth_test_settings(db_auth_stub=True))
    queue: list[tuple[uuid.UUID, ModelProvider]] = []
    app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: queue.append((g, p))
    app.dependency_overrides[get_model_provider] = lambda: MockProvider("ok", app_env="test")
    user = AuthUser(uuid.uuid4(), "commit-response@example.test")
    try:
        async with sessions.begin() as session:
            await seed.load_fixture(session, seed.read_fixture(SAMPLETON))
            destination_id = await session.scalar(
                select(Destination.id).where(Destination.slug == "sampleton")
            )
        assert destination_id is not None
        async with client_for(app) as client:
            created = await client.post(
                "/api/v1/trips",
                json={
                    "title": "Commit timing in Sampleton",
                    "destination_id": str(destination_id),
                    "start_date": "2026-12-04",
                    "end_date": "2026-12-06",
                    "adults": 2,
                },
                headers=user.headers,
            )
            assert created.status_code == 201, created.text
            trip_id = created.json()["id"]
            saved = await client.put(
                f"/api/v1/trips/{trip_id}/preferences",
                json={"interests": ["museum", "food"], "must_visit_place_ids": []},
                headers=user.headers,
            )
            assert saved.status_code == 200, saved.text
            started = await client.post(
                f"/api/v1/trips/{trip_id}/generations",
                json={"mode": "rule_based"},
                headers=user.headers,
            )
            assert started.status_code == 202, started.text
            assert len(queue) == 1
            await jobs.run(*queue.pop(), database.transaction)
            done = await client.get(
                f"/api/v1/generations/{started.json()['id']}", headers=user.headers
            )
            assert done.status_code == 200, done.text
            assert done.json()["status"] == "completed", done.text
            itinerary_url = f"/api/v1/trips/{trip_id}/itinerary"
            initial = await client.get(itinerary_url, headers=user.headers)
            assert initial.status_code == 200, initial.text
            plan = initial.json()
        yield CommittedPlan(
            app,
            user,
            itinerary_url,
            f"/api/v1/itinerary/items/{plan['days'][0]['items'][0]['id']}",
            plan["plan_revision"],
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_edit_is_committed_before_response_and_next_edit_accepts_the_read_revision(
    committed_plan: CommittedPlan,
) -> None:
    plan = committed_plan
    read_at_response: httpx.Response | None = None
    async with client_for(plan.app) as reader:

        async def observe_response(scope: Scope, receive: Receive, send: Send) -> None:
            async def observe(message: Message) -> None:
                nonlocal read_at_response
                await send(message)
                if message["type"] == "http.response.body" and not message.get("more_body", False):
                    # The client has the complete edit response; request teardown has not run yet.
                    read_at_response = await reader.get(
                        plan.itinerary_url, headers=plan.user.headers
                    )

            await plan.app(scope, receive, observe)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=observe_response), base_url="http://test"
        ) as writer:
            edited = await writer.patch(
                plan.item_url,
                json={"plan_revision": plan.revision, "start_time": "10:00"},
                headers=plan.user.headers,
            )
        assert edited.status_code == 200, edited.text
        assert edited.json()["plan_revision"] == plan.revision + 1
        assert read_at_response is not None
        assert read_at_response.status_code == 200, read_at_response.text
        current = read_at_response.json()
        assert current["plan_revision"] == edited.json()["plan_revision"]
        assert current["days"][0]["items"][0]["start_time"] == "10:00"

        immediate = await reader.get(plan.itinerary_url, headers=plan.user.headers)
        assert immediate.status_code == 200, immediate.text
        assert immediate.json()["plan_revision"] == current["plan_revision"]
        second = await reader.patch(
            plan.item_url,
            json={"plan_revision": current["plan_revision"], "start_time": "10:30"},
            headers=plan.user.headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["plan_revision"] == plan.revision + 2
        final = await reader.get(plan.itinerary_url, headers=plan.user.headers)
        assert final.status_code == 200, final.text
        assert final.json()["plan_revision"] == second.json()["plan_revision"]
        assert final.json()["days"][0]["items"][0]["start_time"] == "10:30"


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_the_edit_and_returns_the_error_envelope(
    committed_plan: CommittedPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = committed_plan

    @asynccontextmanager
    async def failed_commit() -> AsyncIterator[AsyncSession]:
        async with database.transaction() as session:

            def fail_before_commit(sync_session: Session) -> None:
                if not sync_session.in_nested_transaction():
                    raise RuntimeError("injected commit failure")

            event.listen(session.sync_session, "before_commit", fail_before_commit)
            yield session

    async with client_for(plan.app) as reader:
        before = await reader.get(plan.itinerary_url, headers=plan.user.headers)
        with monkeypatch.context() as failure:
            failure.setattr(deps, "transaction", failed_commit)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=plan.app, raise_app_exceptions=False),
                base_url="http://test",
            ) as writer:
                response = await writer.patch(
                    plan.item_url,
                    json={"plan_revision": plan.revision, "start_time": "10:00"},
                    headers=plan.user.headers,
                )
        assert response.status_code == 500, response.text
        error = response.json()["error"]
        assert error["code"] == "INTERNAL"
        assert error["request_id"] == response.headers["X-Request-ID"]
        assert error["details"] == []
        assert "injected commit failure" not in response.text
        after = await reader.get(plan.itinerary_url, headers=plan.user.headers)
        assert before.status_code == after.status_code == 200
        assert after.json() == before.json()
