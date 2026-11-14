"""Places service (MOD-B04): read-only use cases behind API-06 and API-16 (basic) (§6.6.3).

The session is the request's transaction (app.auth.deps.DbSession), as in trips/service.py. Only
active destinations and places are read. The seed writes the reference tables; the one write here
is ``ensure_data_source``, the source of a RAG guide (A1 §5.1).
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.db.models import Place
from app.places import repository
from app.places.schemas import Destination, PlaceSummary
from app.schemas.common import Page


class DataSourceConflictError(Exception):
    """A source name already exists with another licence or attribution text (a gate error)."""


async def list_destinations(session: AsyncSession) -> list[Destination]:
    """API-06: the active destinations, ordered by name."""
    return [Destination.from_row(row) for row in await repository.active_destinations(session)]


async def search_places(
    session: AsyncSession,
    destination_id: UUID,
    *,
    q: str | None,
    categories: Sequence[str],
    limit: int,
    offset: int,
) -> Page[PlaceSummary]:
    """API-16: active places of an active destination by name, category and page.

    An inactive or unknown destination is 404 NOT_FOUND: §6.2 makes inactive destinations
    invisible, so they answer like a missing one (IMD-127).
    """
    destination = await repository.destination_by_id(session, destination_id)
    if destination is None or not destination.is_active:
        raise NotFound()
    rows, total = await repository.search_places(
        session,
        destination_id,
        q=q.strip() if q else None,
        categories=categories,
        limit=limit,
        offset=offset,
    )
    return Page[PlaceSummary](
        items=[PlaceSummary.from_row(row, source) for row, source in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def active_place_names(
    session: AsyncSession, destination_id: UUID, place_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """Name by id of the given places that are active in the destination, ordered by name.

    Used by the trips module (IMP-204) to check must-visit places and to name them; an id that
    is missing, inactive or of another destination is simply absent from the result.
    """
    rows = await repository.active_places_by_ids(session, destination_id, place_ids)
    return {row.id: row.name for row in rows}


async def active_places_with_source_date(
    session: AsyncSession, destination_id: UUID
) -> list[tuple[Place, date | None]]:
    """The RAG corpus of a destination's places (A1 §6.2)."""
    return await repository.active_places_with_source_date(session, destination_id)


async def active_places_by_refs(
    session: AsyncSession, destination_slug: str, refs: Sequence[tuple[str, str]]
) -> dict[tuple[str, str], PlaceSummary]:
    """Active places by ``(source_name, external_ref)``; a missing or inactive one is absent."""
    rows = await repository.active_places_by_refs(session, destination_slug, refs)
    return {
        (source, place.external_ref or ""): PlaceSummary.from_row(place) for source, place in rows
    }


async def data_source_terms(
    session: AsyncSession, names: Sequence[str]
) -> dict[str, tuple[str, str | None]]:
    """Licence and attribution text by name, for the sources that exist."""
    rows = await repository.data_sources_by_name(session, names)
    return {row.name: (row.licence, row.attribution_text) for row in rows}


async def ensure_data_source(
    session: AsyncSession,
    name: str,
    source_type: str,
    licence: str,
    url: str | None,
    retrieved_on: date | None,
    attribution_text: str | None,
) -> UUID:
    """The id of the source called ``name``, created if missing (A1 §5.1, §6.3).

    Several pages of one source share this row, and each page URL stays on its own document, so
    an existing row is left as it is. Different terms raise ``DataSourceConflictError``.
    """
    rows = await repository.data_sources_by_name(session, [name])
    if not rows:
        row = await repository.insert_data_source(
            session,
            name=name,
            source_type=source_type,
            licence=licence,
            url=url,
            retrieved_on=retrieved_on,
            attribution_text=attribution_text,
        )
        return row.id
    if (rows[0].licence, rows[0].attribution_text) != (licence, attribution_text):
        raise DataSourceConflictError(name)
    return rows[0].id
