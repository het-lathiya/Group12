"""TC-449: indexing the SAMPLE fixture with MOCK embeddings (Amendment A1 §6.6; IMP-313)."""

import shutil
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderUnavailable
from app.ai.providers.mock import EMBED_MODEL_ID, MockProvider
from app.db.models import DataSource, Destination, Place
from app.db.models.rag import RagChunk, RagDocument
from app.places import seed
from app.places import service as places_service
from app.rag import index as cli
from app.rag import service
from app.rag.service import IndexReport, UnknownDestinationError
from app.schemas.ai import EmbeddingPurpose, EmbeddingResult

REPOSITORY = Path(__file__).resolve().parents[4]
SAMPLETON = REPOSITORY / "data" / "fixtures" / "sampleton"
TODAY = date(2026, 11, 6)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class Embedder(MockProvider):
    """MOCK embeddings that note each call and can fail from a given call on."""

    def __init__(self, fail_from_call: int | None = None) -> None:
        super().__init__("ok", app_env="test")
        self.calls: list[tuple[int, str, Sequence[str | None] | None]] = []
        self.fail_from_call = fail_from_call

    async def embed_texts(
        self,
        texts: Sequence[str],
        purpose: EmbeddingPurpose,
        titles: Sequence[str | None] | None = None,
    ) -> EmbeddingResult:
        if self.fail_from_call is not None and len(self.calls) + 1 >= self.fail_from_call:
            raise ProviderUnavailable("mock provider: embedding outage")
        self.calls.append((len(texts), purpose, titles))
        return await super().embed_texts(texts, purpose, titles)


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A private copy of the SAMPLE guides, so a test can change them."""
    shutil.copytree(SAMPLETON / "guides", tmp_path / "fixtures" / "sampleton" / "guides")
    return tmp_path


@pytest.fixture
def guides(root: Path) -> Path:
    return root / "fixtures" / "sampleton" / "guides"


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


@pytest.fixture
def run(root: Path, sessions: Sessions) -> Callable[..., Any]:
    async def go(provider: Embedder | None = None, **options: Any) -> IndexReport:
        return await service.index(
            options.pop("destination", "sampleton"),
            options.pop("check_only", False),
            options.pop("strict", False),
            provider=provider or Embedder(),
            sessions=sessions,
            root=root,
            today=TODAY,
        )

    return go


async def count(session: AsyncSession, model: Any, *where: Any) -> int:
    return await session.scalar(select(func.count()).select_from(model).where(*where)) or 0


async def chunk_rows(session: AsyncSession, doc_key: str) -> list[RagChunk]:
    query = (
        select(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(RagDocument.doc_key == doc_key)
        .order_by(RagChunk.chunk_index)
        .execution_options(populate_existing=True)
    )
    return list(await session.scalars(query))


@pytest.mark.asyncio
async def test_tc_449_every_place_and_guide_is_chunked_embedded_and_traceable(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    provider = Embedder()

    report = await run(provider)

    places = await count(
        db_session, Place, Place.destination_id == sampleton.id, Place.is_active.is_(True)
    )
    assert report.exit_code == 0
    assert report.documents == places + 3
    assert report.embedded == report.chunks > places + 3
    assert await count(db_session, RagDocument, RagDocument.kind == "place") == places
    assert await count(db_session, RagDocument, RagDocument.kind == "guide") == 3
    assert await count(db_session, RagChunk, RagChunk.embedding.is_(None)) == 0
    assert await count(db_session, RagChunk, RagChunk.embedding_model_id == EMBED_MODEL_ID) == (
        report.chunks
    )

    linked = (
        select(func.count())
        .select_from(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .join(DataSource, DataSource.id == RagDocument.source_id)
    )
    assert await db_session.scalar(linked) == report.chunks

    assert all(size <= 32 for size, _, _ in provider.calls)
    assert {purpose for _, purpose, _ in provider.calls} == {"document"}
    assert all(titles is not None and all(titles) for _, _, titles in provider.calls)


@pytest.mark.asyncio
async def test_a_guide_keeps_its_own_provenance_and_source(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    await run()

    document = await db_session.scalar(
        select(RagDocument).where(RagDocument.doc_key == "guide:sampleton/getting-around")
    )
    assert document is not None
    assert document.title == "SAMPLE getting around Sampleton"
    assert document.retrieved_on == date(2026, 11, 6)
    source = await db_session.get(DataSource, document.source_id)
    assert source is not None
    assert (source.name, source.source_type, source.licence, source.url) == (
        "SAMPLE guides (synthetic)",
        "curated_manual",
        "synthetic test data",
        None,
    )
    assert await count(db_session, DataSource, DataSource.name == source.name) == 1


@pytest.mark.asyncio
async def test_tc_449_a_second_run_embeds_nothing(
    sampleton: Destination, run: Callable[..., Any]
) -> None:
    await run()
    provider = Embedder()

    report = await run(provider)

    assert report.embedded == 0
    assert provider.calls == []


@pytest.mark.asyncio
async def test_tc_449_a_changed_paragraph_re_embeds_only_the_changed_chunks(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    await run()
    key = "guide:sampleton/getting-around"
    before = {row.chunk_index: row.content_sha256 for row in await chunk_rows(db_session, key)}
    path = guides / "getting-around.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("Cycling is popular", "Cycling is well liked"), encoding="utf-8")

    report = await run()

    after = {row.chunk_index: row.content_sha256 for row in await chunk_rows(db_session, key)}
    changed = [index for index, digest in after.items() if before[index] != digest]
    assert changed
    assert len(changed) < len(after)
    assert report.embedded == len(changed)


@pytest.mark.asyncio
async def test_tc_449_a_deleted_guide_goes_inactive_and_its_rows_stay(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    await run()
    key = "guide:sampleton/food-culture"
    chunks = len(await chunk_rows(db_session, key))
    (guides / "food-culture.md").unlink()

    report = await run()

    document = await db_session.scalar(
        select(RagDocument)
        .where(RagDocument.doc_key == key)
        .execution_options(populate_existing=True)
    )
    assert document is not None
    assert document.is_active is False
    rows = await chunk_rows(db_session, key)
    assert len(rows) == chunks
    assert all(row.is_active is False and row.embedding is not None for row in rows)
    assert report.inactive == 1
    assert report.embedded == 0


@pytest.mark.asyncio
async def test_a_restored_guide_is_active_again_without_new_embeddings(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    await run()
    path = guides / "food-culture.md"
    text = path.read_text(encoding="utf-8")
    path.unlink()
    await run()
    path.write_text(text, encoding="utf-8")

    report = await run()

    assert report.embedded == 0
    assert report.inactive == 0
    rows = await chunk_rows(db_session, "guide:sampleton/food-culture")
    assert all(row.is_active for row in rows)


@pytest.mark.asyncio
async def test_chunks_past_the_new_count_go_inactive(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    await run()
    path = guides / "local-customs.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text[: text.index("## Sharing a table")], encoding="utf-8")

    await run()

    rows = await chunk_rows(db_session, "guide:sampleton/local-customs")
    assert [row.is_active for row in rows] == [True, True, False]


@pytest.mark.asyncio
async def test_a_deactivated_place_loses_its_document(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    await run()
    place = await db_session.scalar(select(Place).where(Place.destination_id == sampleton.id))
    assert place is not None
    place.is_active = False
    await db_session.flush()

    report = await run()

    assert report.inactive == 1


@pytest.mark.asyncio
async def test_chunks_of_another_model_are_embedded_again(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    await run()
    [first, *_] = await chunk_rows(db_session, "guide:sampleton/food-culture")
    await db_session.execute(
        update(RagChunk).where(RagChunk.id == first.id).values(embedding_model_id="old-model")
    )

    report = await run()

    assert report.embedded == 1
    rows = await chunk_rows(db_session, "guide:sampleton/food-culture")
    assert rows[0].embedding_model_id == EMBED_MODEL_ID


@pytest.mark.asyncio
async def test_a_provider_error_exits_3_keeps_saved_batches_and_a_re_run_resumes(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    report = await run(Embedder(fail_from_call=2))

    assert report.exit_code == 3
    assert report.provider_failed
    assert report.embedded == 32
    assert await count(db_session, RagChunk, RagChunk.embedding.is_not(None)) == 32

    resumed = await run()

    assert resumed.exit_code == 0
    assert resumed.embedded == report.chunks - 32


@pytest.mark.asyncio
async def test_tc_448_a_strict_gate_error_exits_1_and_writes_nothing(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    path = guides / "food-culture.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA bowl costs £5.\n", encoding="utf-8")
    provider = Embedder()

    report = await run(provider, strict=True)

    assert report.exit_code == 1
    assert [finding.rule for finding in report.findings] == ["currency_amount"]
    assert await count(db_session, RagDocument) == 0
    assert provider.calls == []


@pytest.mark.asyncio
async def test_without_strict_a_warning_indexes_and_an_error_skips_only_that_guide(
    db_session: AsyncSession, sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    path = guides / "food-culture.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA bowl costs £5.\n", encoding="utf-8")
    (guides / "broken.md").write_text("no front matter", encoding="utf-8")

    report = await run()

    assert report.exit_code == 0
    assert (report.warnings, report.errors) == (1, 1)
    assert await count(db_session, RagDocument, RagDocument.kind == "guide") == 3


@pytest.mark.asyncio
async def test_check_validates_and_writes_nothing(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    provider = Embedder()
    sources = await count(db_session, DataSource)

    report = await run(provider, check_only=True, strict=True)

    assert report.exit_code == 0
    assert report.documents > 0
    assert report.embedded == 0
    assert provider.calls == []
    assert await count(db_session, RagDocument) == 0
    assert await count(db_session, DataSource) == sources


@pytest.mark.asyncio
async def test_tc_448_a_stored_source_with_other_terms_is_a_gate_error(
    db_session: AsyncSession, sampleton: Destination, run: Callable[..., Any]
) -> None:
    await places_service.ensure_data_source(
        db_session, "SAMPLE guides (synthetic)", "curated_manual", "CC0", None, None, None
    )

    report = await run(strict=True)

    assert report.exit_code == 1
    assert {finding.rule for finding in report.findings} == {"source_terms"}


@pytest.mark.asyncio
async def test_ensure_data_source_upserts_by_name_and_refuses_other_terms(
    db_session: AsyncSession,
) -> None:
    def ensure(url: str, licence: str = "CC BY-SA 4.0", attribution: str = "Adapted.") -> Any:
        return places_service.ensure_data_source(
            db_session, "A source", "other", licence, url, date(2026, 11, 1), attribution
        )

    first = await ensure("https://example.org/one")

    assert await ensure("https://example.org/two") == first
    assert await count(db_session, DataSource, DataSource.name == "A source") == 1
    with pytest.raises(places_service.DataSourceConflictError):
        await ensure("https://example.org/one", licence="CC0")
    with pytest.raises(places_service.DataSourceConflictError):
        await ensure("https://example.org/one", attribution="Other.")


@pytest.mark.asyncio
async def test_an_unknown_destination_is_refused(
    sampleton: Destination, run: Callable[..., Any]
) -> None:
    with pytest.raises(UnknownDestinationError):
        await run(destination="nowhere")


@pytest.mark.asyncio
async def test_the_report_holds_counts_and_no_guide_text(
    sampleton: Destination, guides: Path, run: Callable[..., Any]
) -> None:
    path = guides / "food-culture.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA bowl costs £5.\n", encoding="utf-8")

    report = await run()

    lines = cli.report_lines(report)
    assert lines[-1].startswith(f"rag-index: documents={report.documents} chunks=")
    assert "warnings=1 errors=0" in lines[-1]
    assert "bowl" not in "\n".join(lines)
    assert "fixtures/sampleton/guides/food-culture.md" in lines[0]


def test_usage_errors_exit_2() -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["--no-such-option"])

    assert caught.value.code == 2
