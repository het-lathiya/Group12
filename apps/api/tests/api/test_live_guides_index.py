"""TC-478 (API): the live guide corpus and the one live index write (A2 §6.5; IMP-726).

A live import writes the destination's place documents and its Wikivoyage and Wikipedia guide
documents in one load, so neither kind deactivates the other. No price, clock time or hours phrase
reaches a stored chunk. The release index (``rag.service.index``) covers curated destinations only
and leaves live documents untouched. An embedding failure leaves the import completed and
retrieval on ``lexical_fallback``. The corpus caps hold (400 chunks per live destination; 5,000
active chunks overall, expired live destinations deactivated first).

Offline only: the SAMPLE fakes or small stubs for live data, the MOCK provider for embeddings. The
job's transactions are savepoints of the test's rolled-back session.
"""

import dataclasses
import json
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pytest
import respx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderUnavailable
from app.ai.providers.mock import EMBED_MODEL_ID, MockProvider
from app.core.config import Settings
from app.db.models import DataSource, Destination, RagChunk, RagDocument
from app.livedata.factory import LiveProviders
from app.livedata.providers.base import LiveDataTimeout, WikiSection
from app.livedata.providers.fake import LIVETON, FakeGeocoder, FakeGuides, FakePlaces
from app.livedata.providers.wiki import WIKIVOYAGE_API, MediaWikiGuides
from app.places import live_import, live_jobs, repository
from app.rag import live_guides
from app.rag import service as rag_service
from app.rag.guides import _CONTENT_RULES

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

LIVETON_USABLE = 44  # place documents of one Liveton import (see test_live_import_jobs.py)
LONG = (
    "The old quarter of narrow lanes climbs from the river towards the hill fort, and its "
    "courtyard houses keep carved wooden balconies above the street. "
)


class StubGuides:
    """A GuideSourceProvider with fixed sections, or an error."""

    def __init__(self, sections: list[WikiSection], error: Exception | None = None) -> None:
        self.sections = sections
        self.error = error

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        if self.error is not None:
            raise self.error
        return self.sections


def section(
    heading: str,
    text: str,
    index: int,
    source: Literal["wikivoyage", "wikipedia"] = "wikivoyage",
) -> WikiSection:
    page_id = 9_000_001 if source == "wikivoyage" else 9_000_011
    host = "en.wikivoyage.org" if source == "wikivoyage" else "en.wikipedia.org"
    return WikiSection(
        source=source,
        page_id=page_id,
        revision_id=page_id * 10,
        page_title="Liveton (SAMPLE)",
        page_url=f"https://{host}/wiki/Liveton_(SAMPLE)",
        index=index,
        heading=heading,
        text=text,
        page_lat=LIVETON.lat,
        page_lon=LIVETON.lon,
    )


RICH = [
    section("Understand", LONG * 4, 1),
    section("See", "Entry costs Rs 50 and it is open 9:00-17:00.\n\n" + LONG * 4, 2),
    section("Eat", LONG * 4, 3),
    section("History", LONG * 4, 1, "wikipedia"),
]


def providers(guides: Any | None = None) -> LiveProviders:
    return LiveProviders(
        geocoder=FakeGeocoder("ok", app_env="test"),
        places=FakePlaces("ok", app_env="test"),
        guides=guides or FakeGuides("ok", app_env="test"),
    )


def never_called() -> LiveProviders:
    """Live-data providers that fail any call: a re-run of a completed city makes none."""
    return LiveProviders(
        geocoder=FakeGeocoder("timeout", app_env="test"),
        places=FakePlaces("timeout", app_env="test"),
        guides=FakeGuides("timeout", app_env="test"),
    )


def embedder(**kwargs: Any) -> MockProvider:
    return MockProvider("ok", app_env="test", **kwargs)


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


async def queued(db_session: AsyncSession, place: Any = LIVETON) -> uuid.UUID:
    row = live_import.build_live_row(place, place.osm_ref)
    return (await repository.insert_live_destination(db_session, row)).id


async def run(
    destination_id: uuid.UUID, sessions: Sessions, guides: Any | None = None, **kwargs: Any
) -> str | None:
    return await live_jobs.run_import(
        destination_id,
        providers=providers(guides),
        sessions=sessions,
        settings=Settings(_env_file=None, app_env="test", ai_provider="MOCK"),
        embedder=kwargs.pop("embedder", embedder()),
    )


async def documents(
    db_session: AsyncSession, destination_id: uuid.UUID, kind: str | None = None
) -> list[RagDocument]:
    query = (
        select(RagDocument)
        .where(RagDocument.destination_id == destination_id)
        .order_by(RagDocument.doc_key)
        .execution_options(populate_existing=True)
    )
    if kind is not None:
        query = query.where(RagDocument.kind == kind)
    return list((await db_session.scalars(query)).all())


async def chunks(db_session: AsyncSession, destination_id: uuid.UUID) -> list[RagChunk]:
    query = (
        select(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(RagDocument.destination_id == destination_id)
        .execution_options(populate_existing=True)
    )
    return list((await db_session.scalars(query)).all())


async def test_live_guides_import_writes_places_and_guides_in_one_load(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)

    assert await run(destination_id, sessions, StubGuides(RICH)) == "completed"

    row = await db_session.get(Destination, destination_id)
    assert row is not None
    places = await documents(db_session, destination_id, "place")
    guides = await documents(db_session, destination_id, "guide")
    assert len(places) == LIVETON_USABLE
    assert all(d.title.startswith("OpenStreetMap: ") for d in places)
    assert [d.doc_key for d in guides] == [
        f"guide:{row.slug}/wikipedia-9000011-1",
        f"guide:{row.slug}/wikivoyage-9000001-1",
        f"guide:{row.slug}/wikivoyage-9000001-2",
    ]
    assert {d.title for d in guides} == {
        "Wikipedia: Liveton (SAMPLE) — History",
        "Wikivoyage: Liveton (SAMPLE) — Understand",
        "Wikivoyage: Liveton (SAMPLE) — See",
    }
    assert all(d.is_active for d in [*places, *guides])
    assert {d.url for d in guides} == {
        "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)",
        "https://en.wikipedia.org/wiki/Liveton_(SAMPLE)",
    }
    stored = await chunks(db_session, destination_id)
    assert all(c.embedding_model_id == EMBED_MODEL_ID for c in stored)
    for chunk in stored:
        for _, pattern in _CONTENT_RULES:
            assert not pattern.search(chunk.content)

    sources = {
        s.name: s
        for s in await db_session.scalars(
            select(DataSource).where(DataSource.name.in_(["Wikivoyage", "Wikipedia"]))
        )
    }
    for name in ("Wikivoyage", "Wikipedia"):
        assert (sources[name].source_type, sources[name].licence) == ("other", "CC BY-SA 4.0")
        assert sources[name].attribution_text == (
            f"Guide text from {name}, by its contributors, under CC BY-SA 4.0; "
            "excerpts, some sections left out"
        )
    assert {d.source_id for d in guides} == {s.id for s in sources.values()}


async def test_live_guides_repeat_import_keeps_both_kinds_active(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions, StubGuides(RICH)) == "completed"
    await repository.requeue_live_import(db_session, destination_id)
    await db_session.flush()

    shorter = [RICH[0]]  # the next run finds one section only
    assert await run(destination_id, sessions, StubGuides(shorter)) == "completed"

    active = [d for d in await documents(db_session, destination_id) if d.is_active]
    assert sum(d.kind == "place" for d in active) == LIVETON_USABLE
    assert [d.doc_key.rsplit("/", 1)[1] for d in active if d.kind == "guide"] == [
        "wikivoyage-9000001-1"
    ]
    inactive = [d for d in await documents(db_session, destination_id) if not d.is_active]
    assert {d.kind for d in inactive} == {"guide"}  # never deleted, only deactivated


async def test_live_guides_release_index_leaves_live_documents_untouched(
    db_session: AsyncSession, sessions: Sessions, tmp_path: Path
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions, StubGuides(RICH)) == "completed"
    before = {
        (d.doc_key, d.is_active, d.content_sha256)
        for d in await documents(db_session, destination_id)
    }
    row = await db_session.get(Destination, destination_id)
    assert row is not None

    await rag_service.index(provider=embedder(), sessions=sessions, root=tmp_path)

    after = {
        (d.doc_key, d.is_active, d.content_sha256)
        for d in await documents(db_session, destination_id)
    }
    assert after == before
    with pytest.raises(rag_service.UnknownDestinationError):
        await rag_service.index(row.slug, provider=embedder(), sessions=sessions, root=tmp_path)


async def test_live_guides_embedding_failure_leaves_the_import_completed_on_lexical_fallback(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    broken = embedder(embed_error=ProviderUnavailable("mock provider: embedding outage"))

    assert await run(destination_id, sessions, StubGuides(RICH), embedder=broken) == "completed"

    row = await db_session.get(Destination, destination_id, populate_existing=True)
    assert row is not None
    assert (row.import_status, row.is_active) == ("completed", True)
    stored = await chunks(db_session, destination_id)
    assert stored
    assert all(c.embedding is None for c in stored)
    assert len(await documents(db_session, destination_id, "guide")) == 3

    place_ids = [d.place_id for d in await documents(db_session, destination_id, "place")]
    result = await rag_service.retrieve(
        rag_service.RetrievalContext(destination_id, "fort and old quarter", place_ids),
        provider=embedder(),
        sessions=sessions,
    )
    assert result.mode == "lexical_fallback"
    assert list(result.guide_passages) == []


async def test_live_guides_source_failure_stores_places_without_guides(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    failing = StubGuides([], error=LiveDataTimeout("guides timed out"))

    assert await run(destination_id, sessions, failing) == "completed"

    assert len(await documents(db_session, destination_id, "place")) == LIVETON_USABLE
    assert await documents(db_session, destination_id, "guide") == []


async def test_live_guides_maxlag_refusal_keeps_the_import_without_guides(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    """HTTP 200 with error code maxlag, through the real MediaWiki client (IMD-218, G15)."""
    destination_id = await queued(db_session)
    recorded = Path(__file__).parents[1] / "fixtures" / "livedata" / "mediawiki_maxlag.json"
    guides = MediaWikiGuides(10, "AITravelPlanner-tests/1.0 (contact: none)")

    with respx.mock() as router:
        route = router.get(WIKIVOYAGE_API).respond(200, json=json.loads(recorded.read_text()))
        assert await run(destination_id, sessions, guides) == "completed"

    assert route.call_count == 1
    assert len(await documents(db_session, destination_id, "place")) == LIVETON_USABLE
    assert await documents(db_session, destination_id, "guide") == []


async def test_live_guides_fake_provider_section_is_indexed(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)

    assert await run(destination_id, sessions) == "completed"

    guides = await documents(db_session, destination_id, "guide")
    assert [d.title for d in guides] == ["Wikivoyage: Liveton (SAMPLE) — Understand"]


async def test_live_guides_global_cap_deactivates_the_oldest_expired_live_destination_first(
    db_session: AsyncSession, sessions: Sessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_id = await queued(db_session)
    assert await run(old_id, sessions, StubGuides(RICH)) == "completed"
    old_chunks = len(await chunks(db_session, old_id))
    await db_session.execute(
        update(Destination)
        .where(Destination.id == old_id)
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    other = dataclasses.replace(LIVETON, osm_ref="R9000003", name="Otherton (SAMPLE)")
    new_id = await queued(db_session, other)
    everything = await db_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(RagDocument.is_active.is_(True), RagChunk.is_active.is_(True))
    )
    assert everything is not None
    # Room for the new destination only once the expired one is deactivated.
    monkeypatch.setattr(live_guides, "RAG_MAX_ACTIVE_CHUNKS", everything + 1)

    assert await run(new_id, sessions, StubGuides(RICH)) == "completed"

    assert not any(d.is_active for d in await documents(db_session, old_id))
    assert not any(c.is_active for c in await chunks(db_session, old_id))
    assert len(await chunks(db_session, new_id)) == old_chunks
    assert all(d.is_active for d in await documents(db_session, new_id))


async def test_live_guides_global_cap_without_room_stores_places_without_guides(
    db_session: AsyncSession, sessions: Sessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination_id = await queued(db_session)
    everything = await db_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(RagDocument.is_active.is_(True), RagChunk.is_active.is_(True))
    )
    assert everything is not None
    monkeypatch.setattr(live_guides, "RAG_MAX_ACTIVE_CHUNKS", everything + LIVETON_USABLE)

    assert await run(destination_id, sessions, StubGuides(RICH)) == "completed"

    assert len(await documents(db_session, destination_id, "place")) == LIVETON_USABLE
    assert await documents(db_session, destination_id, "guide") == []


async def test_live_guides_cli_re_run_embeds_what_an_outage_left_out(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    broken = embedder(embed_error=ProviderUnavailable("mock provider: embedding outage"))
    assert await run(destination_id, sessions, StubGuides(RICH), embedder=broken) == "completed"
    missing = await chunks(db_session, destination_id)

    still_down = await live_import.import_destination(
        osm_ref=LIVETON.osm_ref, providers=never_called(), sessions=sessions, embedder=broken
    )
    assert (still_down.ran, still_down.embedded) == (False, 0)
    assert still_down.embeddings_incomplete
    assert live_import.exit_code(still_down) == live_import.EXIT_OK  # IMD-112
    assert "embedded_on_re_run: 0 (incomplete: provider failed)" in live_import._lines(still_down)

    filled = await live_import.import_destination(
        osm_ref=LIVETON.osm_ref, providers=never_called(), sessions=sessions, embedder=embedder()
    )
    assert (filled.ran, filled.embedded) == (False, len(missing))
    stored = await chunks(db_session, destination_id)
    assert all(c.embedding is not None for c in stored)

    again = await live_import.import_destination(
        osm_ref=LIVETON.osm_ref, providers=never_called(), sessions=sessions, embedder=broken
    )
    assert (again.embedded, again.embeddings_incomplete) == (0, False)  # nothing left, no call


async def test_live_guides_cli_re_run_keeps_another_models_vectors(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions, StubGuides(RICH)) == "completed"
    await db_session.execute(
        update(RagChunk)
        .where(RagChunk.id.in_([c.id for c in await chunks(db_session, destination_id)]))
        .values(embedding_model_id="another-model")
    )

    outcome = await live_import.import_destination(
        osm_ref=LIVETON.osm_ref, providers=never_called(), sessions=sessions, embedder=embedder()
    )

    assert outcome.embedded == 0
    kept = await chunks(db_session, destination_id)
    assert {c.embedding_model_id for c in kept} == {"another-model"}


async def test_live_guides_per_destination_cap_is_400_chunks(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    many = [section(f"Part {n}", LONG * 40, n) for n in range(1, 40)]

    assert await run(destination_id, sessions, StubGuides(many)) == "completed"

    stored = [c for c in await chunks(db_session, destination_id) if c.is_active]
    assert LIVETON_USABLE < len(stored) <= live_guides.LIVE_MAX_CHUNKS_PER_DESTINATION
    assert len(await documents(db_session, destination_id, "place")) == LIVETON_USABLE
