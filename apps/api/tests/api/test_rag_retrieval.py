"""Hybrid retrieval on the SAMPLE fixture with MOCK embeddings (Amendment A1 §6.7, §6.11; IMP-315:
TC-451, TC-452, TC-453, TC-459; FR-137, FR-027 AC2).

The trips are real rows; retrieval uses the job's transactions, as savepoints of the test's
rolled-back session.
"""

import logging
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderUnavailable
from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.db.models import AiGeneration, Destination, Place
from app.db.models.rag import RagChunk
from app.generation import jobs, request_builder, retrieval
from app.generation.presets import meal_slots
from app.places import seed
from app.rag import service as rag_service
from app.rag.service import RetrievalResult
from app.trips import service as trips_service

REPOSITORY = Path(__file__).resolve().parents[4]
SAMPLETON = REPOSITORY / "data" / "fixtures" / "sampleton"
TODAY = date(2026, 11, 6)
NOTE = "lantern bridge at dusk"
LANTERN_BRIDGE = "sample-004"

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]
Job = tuple[uuid.UUID, ModelProvider]


def mock(**options: Any) -> MockProvider:
    return MockProvider("ok", app_env="test", **options)


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


@pytest_asyncio.fixture
async def indexed(sampleton: Destination, sessions: Sessions) -> Destination:
    await rag_service.index(
        "sampleton", provider=mock(), sessions=sessions, root=REPOSITORY / "data", today=TODAY
    )
    return sampleton


async def place(session: AsyncSession, ref: str) -> Place:
    row = await session.scalar(select(Place).where(Place.external_ref == ref))
    assert row is not None
    return row


async def create_trip(
    client: httpx.AsyncClient, user: AuthUser, destination: Destination, **preferences: Any
) -> uuid.UUID:
    answer = await client.patch(
        "/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers
    )
    assert answer.status_code == 200, answer.text
    answer = await client.post(
        "/api/v1/trips",
        json={
            "title": "Weekend in Sampleton",
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-06",
            "adults": 2,
        },
        headers=user.headers,
    )
    assert answer.status_code == 201, answer.text
    trip_id: str = answer.json()["id"]
    defaults = {
        "interests": ["food"],
        "pace": "balanced",
        "budget_priority": "balanced",
        "transport_pref": "walking",
        "accommodation_type": "any",
        "step_free_required": False,
        "notes": NOTE,
        "must_visit_place_ids": [],
    }
    answer = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json=defaults | preferences,
        headers=user.headers,
    )
    assert answer.status_code == 200, answer.text
    return uuid.UUID(trip_id)


async def retrieved_for(
    trip_id: uuid.UUID, user: AuthUser, provider: ModelProvider, sessions: Sessions
) -> RetrievalResult:
    return await request_builder.retrieve(trip_id, user.user_id, provider, sessions)


async def shortlist(
    session: AsyncSession, trip_id: uuid.UUID, user: AuthUser, result: RetrievalResult | None
) -> list[retrieval.Candidate]:
    trip = await trips_service.get_trip(session, user.user_id, trip_id)
    prefs = await trips_service.get_preferences(session, user.user_id, trip_id)
    return await retrieval.ranked_shortlist(
        session,
        trip,
        prefs,
        prefs.must_visit_place_ids,
        meal_slots_per_day=len(meal_slots(prefs.pace)),
        retrieved=result,
    )


def rank(candidates: list[retrieval.Candidate], place_id: uuid.UUID) -> int:
    """Its position, or past the end when the place did not make the shortlist."""
    ids = [candidate.place.id for candidate in candidates]
    return ids.index(place_id) if place_id in ids else len(ids)


@pytest.mark.asyncio
async def test_tc_451_a_place_matching_the_notes_ranks_higher_in_vector_mode_and_repeats(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    result = await retrieved_for(trip_id, auth_user, mock(), sessions)
    bridge = await place(db_session, LANTERN_BRIDGE)

    assert (result.mode, result.embedding_model_id) == ("vector", "mock-embed-v1")
    vector = await shortlist(db_session, trip_id, auth_user, result)
    lexical = await shortlist(db_session, trip_id, auth_user, None)

    assert rank(vector, bridge.id) < rank(lexical, bridge.id)
    again = await retrieved_for(trip_id, auth_user, mock(), sessions)
    repeated = await shortlist(db_session, trip_id, auth_user, again)
    assert [c.place.id for c in repeated] == [c.place.id for c in vector]


@pytest.mark.asyncio
async def test_every_candidate_gets_its_best_chunk_and_similarity(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    db_session: AsyncSession,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    result = await retrieved_for(trip_id, auth_user, mock(), sessions)
    candidates = await shortlist(db_session, trip_id, auth_user, None)

    assert {c.place.id for c in candidates} <= set(result.place_best_chunk)
    assert result.place_similarity.keys() == result.place_best_chunk.keys()
    for place_id, chunk in result.place_best_chunk.items():
        assert chunk.place_id == place_id
        assert chunk.similarity == result.place_similarity[place_id]


@pytest.mark.asyncio
async def test_an_inactive_chunk_is_not_searched(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    db_session: AsyncSession,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    first = await retrieved_for(trip_id, auth_user, mock(), sessions)
    bridge = await place(db_session, LANTERN_BRIDGE)
    await db_session.execute(
        update(RagChunk)
        .where(RagChunk.id == first.place_best_chunk[bridge.id].chunk_id)
        .values(is_active=False)
    )

    second = await retrieved_for(trip_id, auth_user, mock(), sessions)

    assert bridge.id not in second.place_similarity
    assert second.mode == "vector"


@pytest.mark.asyncio
async def test_tc_451_filters_and_must_visit_are_unchanged_by_the_semantic_part(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    must = await place(db_session, LANTERN_BRIDGE)  # step_free false, and far from these notes
    trip_id = await create_trip(
        api_client,
        auth_user,
        indexed,
        notes="museum",
        interests=["museum"],
        step_free_required=True,
        must_visit_place_ids=[str(must.id)],
    )
    result = await retrieved_for(trip_id, auth_user, mock(), sessions)

    vector = await shortlist(db_session, trip_id, auth_user, result)

    assert result.mode == "vector"
    # The must-visit place is the least similar; compare within 1e-6 because float
    # rounding of the cosine differs by platform (about 4e-9 on Apple Silicon).
    least = min(result.place_similarity.values())
    assert abs(result.place_similarity[must.id] - least) <= 1e-6
    assert must.id in {c.place.id for c in vector}
    assert {c.place.step_free for c in vector if not c.must_visit} == {True}
    lexical = await shortlist(db_session, trip_id, auth_user, None)
    assert {c.place.id for c in vector} <= {c.place.id for c in lexical} | {must.id}


@pytest.mark.asyncio
async def test_tc_453_guide_passages_hold_at_most_two_chunks_per_document(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)

    result = await retrieved_for(trip_id, auth_user, mock(), sessions)

    assert 0 < len(result.guide_passages) <= 6
    assert max(Counter(c.document_id for c in result.guide_passages).values()) <= 2
    assert {c.place_id for c in result.guide_passages} == {None}


@pytest.mark.asyncio
async def test_tc_452_a_failing_query_embedding_gives_lexical_fallback(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
    caplog: pytest.LogCaptureFixture,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    failing = mock(embed_error=ProviderUnavailable("mock provider: embedding outage"))

    with caplog.at_level(logging.WARNING):
        result = await retrieved_for(trip_id, auth_user, failing, sessions)

    assert result.mode == "lexical_fallback"
    assert (result.place_similarity, result.guide_passages) == ({}, [])
    assert "provider_unavailable" in caplog.text
    assert NOTE not in caplog.text


@pytest.mark.asyncio
async def test_tc_452_an_empty_index_gives_lexical_fallback(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    sampleton: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    result = await retrieved_for(trip_id, auth_user, mock(), sessions)
    assert result.mode == "lexical_fallback"


@pytest.mark.asyncio
async def test_tc_452_chunks_of_another_embedding_model_are_not_used(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    db_session: AsyncSession,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    await db_session.execute(update(RagChunk).values(embedding_model_id="another-model"))

    result = await retrieved_for(trip_id, auth_user, mock(), sessions)

    assert result.mode == "lexical_fallback"


@pytest.mark.asyncio
async def test_a_database_error_during_retrieval_gives_lexical_fallback(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)

    async def broken(*args: Any) -> None:
        raise OperationalError("select", {}, Exception("connection lost"))

    monkeypatch.setattr(rag_service.repository, "best_place_chunks", broken)

    result = await retrieved_for(trip_id, auth_user, mock(), sessions)

    assert result.mode == "lexical_fallback"


@pytest.mark.asyncio
@pytest.mark.parametrize("embed_error", [None, ProviderUnavailable("mock provider: outage")])
async def test_tc_452_tc_459_the_generation_completes_and_retrieval_is_timed(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    db_session: AsyncSession,
    indexed: Destination,
    sessions: Sessions,
    embed_error: ProviderUnavailable | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    queue: list[Job] = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda gid, p: queue.append((gid, p))
    api_app.dependency_overrides[get_model_provider] = lambda: mock(embed_error=embed_error)

    started = await api_client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": "ai"}, headers=auth_user.headers
    )
    assert started.status_code == 202, started.text
    with caplog.at_level(logging.INFO):
        await jobs.run(*queue.pop(0), sessions)

    row = await db_session.get(
        AiGeneration, uuid.UUID(started.json()["id"]), populate_existing=True
    )
    assert row is not None
    assert (row.status, row.outcome) == ("completed", "model")
    expected = "lexical_fallback" if embed_error else "vector"
    assert f"retrieval {expected} in " in caplog.text
    assert NOTE not in caplog.text

    # TC-459, FR-138 AC3: the record and API-23 name the mode, the model and the time.
    assert (row.input_schema_version, row.output_schema_version) == ("gr-2", "io-2")
    assert row.retrieval_mode == expected
    assert row.embedding_model_id == "mock-embed-v1"
    assert row.retrieval_ms is not None
    assert row.retrieval_ms >= 0
    sent = row.generation_settings["passages_sent"]
    assert sent == 0 if embed_error else 0 < sent <= 12
    assert row.generation_settings["passages_dropped"] == 0
    assert row.validation_summary["unknown_source_ids"] == 0
    read = await api_client.get(f"/api/v1/generations/{row.id}", headers=auth_user.headers)
    body = read.json()
    assert (body["retrieval_mode"], body["embedding_model_id"]) == (expected, "mock-embed-v1")
    assert body["retrieval_ms"] == row.retrieval_ms


@pytest.mark.asyncio
async def test_tc_459_retrieval_ms_is_set(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    indexed: Destination,
    sessions: Sessions,
) -> None:
    trip_id = await create_trip(api_client, auth_user, indexed)
    result = await retrieved_for(trip_id, auth_user, mock(), sessions)
    assert isinstance(result.retrieval_ms, int)
    assert result.retrieval_ms >= 0
