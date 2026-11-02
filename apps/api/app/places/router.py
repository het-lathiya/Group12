"""Place routes API-06 and API-16 (basic) (specification §6.6.3; FR-007, FR-016, FR-019).

Mounted under /api/v1, whose router requires CurrentUser (IMP-108): reference data still needs a
token (§6.2). API-16 has the basic filters the must-visit picker needs (destination_id, q,
category, paging); IMP-509 and IMP-604 add the others.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import DbSession
from app.places import repository
from app.places.schemas import Destination, PlaceSummary
from app.places.vocabulary import OfferedCategory
from app.schemas.common import Page

router = APIRouter(tags=["places"])


@router.get(
    "/destinations",
    response_model=list[Destination],
    summary="API-06 List the supported destinations",
)
async def list_destinations(session: DbSession) -> list[Destination]:
    return [Destination.from_row(row) for row in await repository.active_destinations(session)]


@router.get("/places", response_model=Page[PlaceSummary], summary="API-16 Search places")
async def search_places(
    session: DbSession,
    destination_id: UUID,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    category: Annotated[list[OfferedCategory] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[PlaceSummary]:
    rows, total = await repository.search_places(
        session,
        destination_id,
        q=q.strip() if q else None,
        categories=[c.value for c in category or []],
        limit=limit,
        offset=offset,
    )
    return Page[PlaceSummary](
        items=[PlaceSummary.from_row(row) for row in rows], total=total, limit=limit, offset=offset
    )
