"""Place routes API-06, API-16 and API-17 (specification §6.6.3; FR-007, FR-016 to FR-019).

Mounted under /api/v1, whose router requires CurrentUser (IMP-108): reference data still needs a
token (§6.2). API-16 has the must-visit picker's filters (IMP-205), the source name (IMP-509) and
the IMP-604 filters (interest tags, price, duration, step-free, distance); API-17 reads one place
with its hours, source and labels (IMP-604). The handlers only call places/service.py.

API-19 to API-21 (IMP-605) are declared with their final shapes and answer 501 NOT_IMPLEMENTED
until that card builds them (IMD-37).
"""

from decimal import Decimal
from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.auth.deps import DbSession
from app.core.errors import EndpointNotImplemented, ValidationFailed
from app.core.rate_limit import expensive_request
from app.places import service
from app.places.schemas import Destination, PlaceOut, PlaceSummary
from app.places.vocabulary import OfferedCategory, Tag
from app.schemas.common import ErrorDetail, Page

router = APIRouter(tags=["places"])


@router.get(
    "/destinations",
    response_model=list[Destination],
    summary="API-06 List the supported destinations",
)
async def list_destinations(session: DbSession) -> list[Destination]:
    return await service.list_destinations(session)


# IMP-604 step 1: a query parameter API-16 does not declare is refused, never ignored.
SEARCH_PARAMS: Final = frozenset(
    {
        "destination_id",
        "q",
        "category",
        "interest",
        "price_max",
        "duration_max_min",
        "step_free",
        "near_lat",
        "near_lon",
        "max_distance_m",
        "limit",
        "offset",
    }
)


def known_search_params(request: Request) -> None:
    unknown = sorted(set(request.query_params) - SEARCH_PARAMS)
    if unknown:
        raise ValidationFailed(
            details=[
                ErrorDetail(field=name, message="Unknown query parameter.") for name in unknown
            ]
        )


@router.get(
    "/places",
    response_model=Page[PlaceSummary],
    summary="API-16 Search places",
    dependencies=[Depends(known_search_params), Depends(expensive_request)],
)
async def search_places(
    session: DbSession,
    destination_id: UUID,
    q: Annotated[
        str | None, Query(min_length=1, max_length=80, description="Name or tag contains")
    ] = None,
    category: Annotated[list[OfferedCategory] | None, Query()] = None,
    interest: Annotated[
        list[Tag] | None, Query(description="Places with any of these tags")
    ] = None,
    price_max: Annotated[
        Decimal | None,
        Query(ge=0, max_digits=12, decimal_places=2, description="In the destination currency"),
    ] = None,
    duration_max_min: Annotated[int | None, Query(ge=15, le=480)] = None,
    step_free: Annotated[bool, Query(description="True keeps confirmed step-free places")] = False,
    near_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    near_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    max_distance_m: Annotated[int | None, Query(ge=1, le=100_000)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[PlaceSummary]:
    return await service.search_places(
        session,
        destination_id,
        q=q,
        categories=[c.value for c in category or []],
        tags=[t.value for t in interest or []],
        price_max=price_max,
        duration_max_min=duration_max_min,
        step_free=step_free,
        near_lat=near_lat,
        near_lon=near_lon,
        max_distance_m=max_distance_m,
        limit=limit,
        offset=offset,
    )


@router.get("/places/{place_id}", response_model=PlaceOut, summary="API-17 Read one place")
async def get_place(session: DbSession, place_id: UUID, trip_id: UUID | None = None) -> PlaceOut:
    return await service.get_place(session, place_id)


@router.put(
    "/trips/{trip_id}/saved-places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="API-19 Save a place to my trip",
)
async def save_place(trip_id: UUID, place_id: UUID) -> None:
    raise EndpointNotImplemented()


@router.delete(
    "/trips/{trip_id}/saved-places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="API-20 Remove a saved place from my trip",
)
async def unsave_place(trip_id: UUID, place_id: UUID) -> None:
    raise EndpointNotImplemented()


@router.get(
    "/trips/{trip_id}/saved-places",
    response_model=list[PlaceSummary],
    summary="API-21 List my trip's saved places",
)
async def list_saved_places(trip_id: UUID) -> list[PlaceSummary]:
    raise EndpointNotImplemented()
