"""rag_documents and rag_chunks (migration 0007). MOD-B18 is their only writer (A1 §8.1).

Documents and chunks are deactivated, never deleted, so saved citations keep resolving (IMD-110).
The similarity queries are exact cosine over the destination's active chunks of one embedding model;
there is no approximate index (IMD-107).
"""

from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Row, func, or_, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rag import RagChunk, RagDocument
from app.rag.chunker import Chunk
from app.rag.documents import CorpusDocument
from app.rag.mmr import RetrievedChunk


def _apply(row: RagChunk, chunk: Chunk) -> None:
    row.heading = chunk.heading
    row.content = chunk.content
    row.content_sha256 = chunk.sha256
    row.token_estimate = chunk.token_estimate
    row.embedding = None
    row.embedding_model_id = None
    row.embedded_at = None


async def save_document(
    session: AsyncSession, destination_id: UUID, document: CorpusDocument, source_id: UUID
) -> None:
    """Upsert by doc_key and chunks by index. A chunk whose hash changed loses its embedding."""
    row = await session.scalar(select(RagDocument).where(RagDocument.doc_key == document.doc_key))
    if row is None:
        row = RagDocument(doc_key=document.doc_key, kind=document.kind)
        session.add(row)
    row.destination_id = destination_id
    row.place_id = document.place_id
    row.source_id = source_id
    row.title = document.title
    row.url = document.url
    row.retrieved_on = document.retrieved_on
    row.content_sha256 = document.content_sha256
    row.is_active = True
    await session.flush()

    stored = {
        chunk.chunk_index: chunk
        for chunk in await session.scalars(select(RagChunk).where(RagChunk.document_id == row.id))
    }
    for chunk in document.chunks:
        existing = stored.pop(chunk.index, None)
        if existing is None:
            existing = RagChunk(document_id=row.id, chunk_index=chunk.index)
            _apply(existing, chunk)
            session.add(existing)
        elif existing.content_sha256 != chunk.sha256:
            _apply(existing, chunk)
        existing.is_active = True
    for leftover in stored.values():
        leftover.is_active = False
    await session.flush()


async def deactivate_missing(
    session: AsyncSession, destination_id: UUID, keep: Collection[str]
) -> None:
    """Documents of the destination no longer in the corpus, with their chunks, go inactive."""
    gone = select(RagDocument.id).where(
        RagDocument.destination_id == destination_id,
        RagDocument.is_active.is_(True),
        RagDocument.doc_key.not_in(list(keep)),
    )
    ids = list(await session.scalars(gone))
    if ids:
        await session.execute(
            update(RagChunk).where(RagChunk.document_id.in_(ids)).values(is_active=False)
        )
        await session.execute(
            update(RagDocument).where(RagDocument.id.in_(ids)).values(is_active=False)
        )


async def count_inactive_documents(session: AsyncSession, destination_ids: Sequence[UUID]) -> int:
    query = select(func.count()).where(
        RagDocument.destination_id.in_(list(destination_ids)), RagDocument.is_active.is_(False)
    )
    return await session.scalar(query) or 0


async def pending_chunks(
    session: AsyncSession, model_id: str, destination_ids: Sequence[UUID]
) -> list[tuple[UUID, str, str]]:
    """(id, content, document title) of active chunks with no embedding from ``model_id``."""
    query = (
        select(RagChunk.id, RagChunk.content, RagDocument.title)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(
            RagDocument.destination_id.in_(list(destination_ids)),
            RagDocument.is_active.is_(True),
            RagChunk.is_active.is_(True),
            or_(RagChunk.embedding.is_(None), RagChunk.embedding_model_id != model_id),
        )
        .order_by(RagDocument.doc_key, RagChunk.chunk_index)
    )
    return [(row[0], row[1], row[2]) for row in await session.execute(query)]


async def store_embeddings(
    session: AsyncSession,
    chunk_ids: Sequence[UUID],
    vectors: Sequence[Sequence[float]],
    model_id: str,
) -> None:
    for chunk_id, vector in zip(chunk_ids, vectors, strict=True):
        await session.execute(
            update(RagChunk)
            .where(RagChunk.id == chunk_id)
            .values(embedding=list(vector), embedding_model_id=model_id, embedded_at=func.now())
        )


def _searchable(destination_id: UUID, model_id: str, kind: str) -> tuple[ColumnElement[bool], ...]:
    return (
        RagDocument.destination_id == destination_id,
        RagDocument.kind == kind,
        RagDocument.is_active.is_(True),
        RagChunk.is_active.is_(True),
        RagChunk.embedding_model_id == model_id,
    )


def _chunk(row: Row[Any], vector: Sequence[float] = ()) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=row.id,
        document_id=row.document_id,
        place_id=row.place_id,
        title=row.title,
        content=row.content,
        similarity=float(row.similarity),
        vector=vector,
    )


async def best_place_chunks(
    session: AsyncSession,
    destination_id: UUID,
    model_id: str,
    query_vector: Sequence[float],
    place_ids: Sequence[UUID],
) -> list[RetrievedChunk]:
    """The most similar chunk of each of these places that has one (ties by chunk ID)."""
    distance = RagChunk.embedding.cosine_distance(query_vector)
    query = (
        select(
            RagChunk.id,
            RagChunk.document_id,
            RagDocument.place_id,
            RagDocument.title,
            RagChunk.content,
            (1 - distance).label("similarity"),
        )
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(*_searchable(destination_id, model_id, "place"))
        .where(RagDocument.place_id.in_(list(place_ids)))
        .ext(distinct_on(RagDocument.place_id))
        .order_by(RagDocument.place_id, distance, RagChunk.id)
    )
    return [_chunk(row) for row in await session.execute(query)]


async def top_guide_chunks(
    session: AsyncSession,
    destination_id: UUID,
    model_id: str,
    query_vector: Sequence[float],
    limit: int,
) -> list[RetrievedChunk]:
    """The most similar guide chunks with their vectors, best first (ties by chunk ID)."""
    distance = RagChunk.embedding.cosine_distance(query_vector)
    query = (
        select(
            RagChunk.id,
            RagChunk.document_id,
            RagDocument.place_id,
            RagDocument.title,
            RagChunk.content,
            RagChunk.embedding,
            (1 - distance).label("similarity"),
        )
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(*_searchable(destination_id, model_id, "guide"))
        .order_by(distance, RagChunk.id)
        .limit(limit)
    )
    return [_chunk(row, [float(x) for x in row.embedding]) for row in await session.execute(query)]
