"""Any-city routes API-76 to API-79 (Amendment A2 §5), mounted only when ``any_city_mode`` is ON.

``app.main.create_app`` includes this router under ``/api/v1`` (bearer dependency) only when the
switch is ON, so with the switch OFF its paths answer 404 NOT_FOUND and ``openapi.v1.json`` is
unchanged (A2 §3.3). Destinations are reference data for every signed-in user. ``/search`` is
declared before ``/{destination_id}``. The handlers only call ``places/live_service.py``.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.auth.deps import CurrentUser, DbSession
from app.core.config import Settings
from app.core.rate_limit import expensive_request
from app.livedata.factory import get_geocoder
from app.livedata.providers.base import GeocodingProvider
from app.places import live_service
from app.places.live_schemas import (
    CitySearchOut,
    DestinationDetailOut,
    LiveDestinationOut,
    ResolveCityIn,
)
from app.places.live_service import ImportSubmitter, get_import_submitter

router = APIRouter(tags=["any-city"])

GeocoderDep = Annotated[GeocodingProvider, Depends(get_geocoder)]
SubmitterDep = Annotated[ImportSubmitter, Depends(get_import_submitter)]


@router.get(
    "/destinations/search",
    response_model=CitySearchOut,
    dependencies=[Depends(expensive_request)],
    summary="API-76 Search for a city",
)
async def search_cities(
    session: DbSession,
    geocoder: GeocoderDep,
    q: Annotated[str, Query(description="City name, 2 to 100 characters after trimming")],
) -> CitySearchOut:
    return await live_service.search(session, geocoder, q)


@router.post(
    "/destinations/resolve",
    response_model=LiveDestinationOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"model": LiveDestinationOut, "description": "The destination exists"}},
    summary="API-77 Resolve a city into a live destination",
)
async def resolve_city(
    body: ResolveCityIn,
    request: Request,
    response: Response,
    user: CurrentUser,
    session: DbSession,
    geocoder: GeocoderDep,
    submit: SubmitterDep,
) -> LiveDestinationOut:
    settings: Settings = request.app.state.settings
    result = await live_service.resolve(
        session, settings, user.user_id, body.osm_ref, geocoder, submit
    )
    if not result.queued:
        response.status_code = status.HTTP_200_OK
    return result.destination


@router.get(
    "/destinations/{destination_id}/import",
    response_model=LiveDestinationOut,
    summary="API-78 Read a live destination's import status",
)
async def get_import_status(destination_id: UUID, session: DbSession) -> LiveDestinationOut:
    return await live_service.import_state(session, destination_id)


@router.get(
    "/destinations/{destination_id}",
    response_model=DestinationDetailOut,
    summary="API-79 Read one destination",
)
async def get_destination(destination_id: UUID, session: DbSession) -> DestinationDetailOut:
    return await live_service.destination_detail(session, destination_id)
