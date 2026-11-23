"""Any-city routes API-76 to API-79, the API-06 curated filter and the trip rule (IMP-725).

TC-472, TC-473, TC-476, TC-477 (Amendment A2 §5, §6.1). The app is built with ``any_city_mode`` ON
through a settings override (the autouse ``clean_settings_env`` fixture clears the environment),
on the rolled-back test session. The geocoder is the offline SAMPLE fake ("Liveton (SAMPLE)",
R9000001; "Tinyham (SAMPLE)", R9000002) or a small stub; the import runner is replaced by a
recorder, so no job runs here (the job is covered by ``test_live_import_jobs.py``).
"""

import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser, auth_test_settings, client_for
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import deps
from app.db.models import DataSource, Destination, Place
from app.livedata.factory import get_geocoder
from app.livedata.providers.base import BBox, GeoCandidate, GeoPlace, LiveDataUnavailable
from app.livedata.providers.fake import FakeGeocoder
from app.main import create_app
from app.places import live_service, seed
from app.places.live_service import get_import_submitter, live_slug

pytestmark = pytest.mark.any_city

SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"
V1 = "/api/v1"
LIVETON = "R9000001"
TINYHAM = "R9000002"


class StubGeocoder:
    """A geocoder with one fixed lookup answer, and a search that counts its calls."""

    def __init__(self, place: GeoPlace | None = None, *, fail: bool = False) -> None:
        self.place = place
        self.fail = fail
        self.searches = 0

    async def search(self, q: str) -> list[GeoCandidate]:
        self.searches += 1
        if self.fail:
            raise LiveDataUnavailable("http 503")
        return [
            GeoCandidate(
                "R9000001",
                "Liveton (SAMPLE)",
                "Liveton (SAMPLE), India",
                None,
                "IN",
                23.5,
                77.5,
                "city",
            ),
            GeoCandidate(
                "N9000102",
                "Liveton Junction (SAMPLE)",
                "Junction, India",
                None,
                "IN",
                23.4,
                77.4,
                "village",
            ),
        ] + [
            GeoCandidate(
                f"N91{i:05d}", f"Sample Hamlet {i}", f"Hamlet {i}", None, "IN", 23.0, 77.0, "town"
            )
            for i in range(10)
        ]

    async def lookup(self, osm_ref: str) -> GeoPlace | None:
        if self.fail:
            raise LiveDataUnavailable("http 503")
        return self.place


def _place(**changes: Any) -> GeoPlace:
    values: dict[str, Any] = {
        "osm_ref": "R9000009",
        "name": "Stubtown (SAMPLE)",
        "name_en": None,
        "display_name": "Stubtown (SAMPLE), India",
        "region": "Sample State",
        "country_code": "IN",
        "lat": 23.5,
        "lon": 77.5,
        "kind": "city",
        "bbox": BBox(south=22.0, west=76.0, north=25.0, east=79.0),
    }
    values.update(changes)
    return GeoPlace(**values)


class Live:
    def __init__(self, app: FastAPI, client: httpx.AsyncClient) -> None:
        self.app = app
        self.client = client
        self.submitted: list[uuid.UUID] = []

    def use_geocoder(self, geocoder: object) -> None:
        self.app.dependency_overrides[get_geocoder] = lambda: geocoder


@pytest.fixture(autouse=True)
def _empty_search_cache() -> Iterator[None]:
    live_service.search_cache.clear()
    yield
    live_service.search_cache.clear()


async def _live(db_session: AsyncSession, **settings: Any) -> AsyncIterator[Live]:
    app = create_app(auth_test_settings(features_disabled="!any_city_mode", **settings))

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[deps.db_session] = test_session
    async with client_for(app) as client:
        live = Live(app, client)
        app.dependency_overrides[get_import_submitter] = lambda: live.submitted.append
        live.use_geocoder(FakeGeocoder("ok", app_env="test"))
        yield live


@pytest_asyncio.fixture
async def live(db_session: AsyncSession) -> AsyncIterator[Live]:
    async for value in _live(db_session):
        yield value


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


async def _resolve(live: Live, user: AuthUser, osm_ref: str = LIVETON) -> httpx.Response:
    return await live.client.post(
        f"{V1}/destinations/resolve", json={"osm_ref": osm_ref}, headers=user.headers
    )


async def _complete(session: AsyncSession, destination_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(Destination)
        .where(Destination.id == destination_id)
        .values(
            import_status="completed",
            is_active=True,
            imported_at=now,
            expires_at=now + timedelta(days=30),
            places_found=48,
            places_usable=44,
        )
    )


# ---------- TC-472 API-76 search ----------


@pytest.mark.asyncio
async def test_tc_472_search_returns_settlements_marked_when_known(
    live: Live, auth_user: AuthUser
) -> None:
    response = await live.client.get(
        f"{V1}/destinations/search", params={"q": "  Liveton  "}, headers=auth_user.headers
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["osm_ref"] for r in results] == [LIVETON]
    assert results[0]["kind"] == "city"
    assert results[0]["destination_id"] is None
    assert results[0]["data_tier"] is None

    resolved = await _resolve(live, auth_user)
    again = await live.client.get(
        f"{V1}/destinations/search", params={"q": "liveton"}, headers=auth_user.headers
    )
    assert again.json()["results"][0]["destination_id"] == resolved.json()["destination_id"]
    assert again.json()["results"][0]["data_tier"] == "live"


@pytest.mark.asyncio
async def test_tc_472_search_caps_at_eight_and_serves_a_repeat_from_the_cache(
    live: Live, auth_user: AuthUser
) -> None:
    stub = StubGeocoder()
    live.use_geocoder(stub)
    first = await live.client.get(
        f"{V1}/destinations/search", params={"q": "Liveton"}, headers=auth_user.headers
    )
    second = await live.client.get(
        f"{V1}/destinations/search", params={"q": " liveton "}, headers=auth_user.headers
    )
    assert first.status_code == second.status_code == 200
    assert len(first.json()["results"]) == 8
    assert first.json() == second.json()
    assert stub.searches == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("q", ["", " a ", "x" * 101, "\x00\x01b"])
async def test_tc_472_search_validates_q(live: Live, auth_user: AuthUser, q: str) -> None:
    response = await live.client.get(
        f"{V1}/destinations/search", params={"q": q}, headers=auth_user.headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_tc_472_search_answers_503_when_the_geocoder_is_down(
    live: Live, auth_user: AuthUser
) -> None:
    live.use_geocoder(FakeGeocoder("timeout", app_env="test"))
    response = await live.client.get(
        f"{V1}/destinations/search", params={"q": "Liveton"}, headers=auth_user.headers
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tc_472_search_answers_429_when_the_limiter_trips(
    db_session: AsyncSession, auth_user: AuthUser
) -> None:
    async for live in _live(db_session, rate_limit_per_min=1):
        ok = await live.client.get(
            f"{V1}/destinations/search", params={"q": "Liveton"}, headers=auth_user.headers
        )
        limited = await live.client.get(
            f"{V1}/destinations/search", params={"q": "Liveton"}, headers=auth_user.headers
        )
        assert ok.status_code == 200
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"


# ---------- TC-473 API-77 resolve ----------


@pytest.mark.asyncio
async def test_tc_473_new_settlement_is_queued_once_and_repeats_answer_200(
    live: Live, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    first = await _resolve(live, auth_user)
    assert first.status_code == 202
    body = first.json()
    assert body["data_tier"] == "live"
    assert body["import"]["status"] == "queued"
    assert body["currency"] == "INR"
    assert body["timezone"] == "Asia/Kolkata"
    assert body["slug"] == live_slug(body["name"], LIVETON)
    assert "import_requested_by" not in body
    assert live.submitted == [uuid.UUID(body["destination_id"])]

    second = await _resolve(live, auth_user)
    assert second.status_code == 200
    assert second.json()["destination_id"] == body["destination_id"]
    assert len(live.submitted) == 1

    row = await db_session.get(Destination, uuid.UUID(body["destination_id"]))
    assert row is not None
    assert row.is_active is False
    assert row.import_requested_by == auth_user.user_id
    assert row.provider == "osm"
    assert row.external_ref == LIVETON


@pytest.mark.asyncio
async def test_tc_473_bbox_is_clipped_around_the_centre(
    live: Live, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    live.use_geocoder(StubGeocoder(_place()))
    response = await _resolve(live, auth_user, "R9000009")
    assert response.status_code == 202
    row = await db_session.get(Destination, uuid.UUID(response.json()["destination_id"]))
    assert row is not None
    assert row.bbox_max_lat - row.bbox_min_lat <= Decimal("0.500001")
    assert row.bbox_min_lat < row.center_lat < row.bbox_max_lat


@pytest.mark.asyncio
async def test_tc_473_failed_import_is_queued_again(
    live: Live, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    first = await _resolve(live, auth_user)
    destination_id = uuid.UUID(first.json()["destination_id"])
    await db_session.execute(
        update(Destination)
        .where(Destination.id == destination_id)
        .values(import_status="failed", import_failure_reason="timeout")
    )
    again = await _resolve(live, auth_user)
    assert again.status_code == 202
    assert again.json()["import"]["status"] == "queued"
    assert again.json()["import"]["failure_reason"] is None
    assert live.submitted == [destination_id, destination_id]


@pytest.mark.asyncio
async def test_tc_473_unknown_reference_is_404(live: Live, auth_user: AuthUser) -> None:
    response = await _resolve(live, auth_user, "R9999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"kind": "suburb"}, "Choose a city, town or village"),
        ({"country_code": "ZZ"}, "This country is not supported yet"),
    ],
)
async def test_tc_473_non_settlement_or_unsupported_country_is_422(
    live: Live, auth_user: AuthUser, changes: dict[str, Any], message: str
) -> None:
    live.use_geocoder(StubGeocoder(_place(**changes)))
    response = await _resolve(live, auth_user, "R9000009")
    assert response.status_code == 422
    assert response.json()["error"]["message"] == message
    assert live.submitted == []


@pytest.mark.asyncio
@pytest.mark.parametrize("osm_ref", ["9000001", "X1", "R", "R1234567890123", "R1;drop"])
async def test_tc_473_reference_format_is_validated(
    live: Live, auth_user: AuthUser, osm_ref: str
) -> None:
    response = await _resolve(live, auth_user, osm_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tc_473_geocoder_down_is_503(live: Live, auth_user: AuthUser) -> None:
    live.use_geocoder(StubGeocoder(fail=True))
    response = await _resolve(live, auth_user, "R9000009")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_tc_473_daily_cap_per_user_is_429(
    db_session: AsyncSession, auth_user: AuthUser
) -> None:
    async for live in _live(db_session, live_daily_imports_per_user=1):
        assert (await _resolve(live, auth_user, LIVETON)).status_code == 202
        capped = await _resolve(live, auth_user, TINYHAM)
        assert capped.status_code == 429
        assert capped.json()["error"]["code"] == "RATE_LIMITED"
        # Resolving an existing destination does not count against the cap.
        assert (await _resolve(live, auth_user, LIVETON)).status_code == 200


@pytest.mark.asyncio
async def test_tc_473_daily_cap_global_is_429(
    db_session: AsyncSession, auth_user: AuthUser
) -> None:
    async for live in _live(db_session, live_daily_imports_global=1):
        assert (await _resolve(live, auth_user, LIVETON)).status_code == 202
        assert (await _resolve(live, auth_user, TINYHAM)).status_code == 429


# ---------- TC-476 API-78, API-79 and API-06 ----------


@pytest.mark.asyncio
async def test_tc_476_import_status_for_live_and_404_for_curated(
    live: Live, auth_user: AuthUser, sampleton: Destination
) -> None:
    resolved = await _resolve(live, auth_user)
    destination_id = resolved.json()["destination_id"]
    status = await live.client.get(
        f"{V1}/destinations/{destination_id}/import", headers=auth_user.headers
    )
    assert status.status_code == 200
    assert status.json()["import"]["status"] == "queued"
    for unknown in (sampleton.id, uuid.uuid4()):
        response = await live.client.get(
            f"{V1}/destinations/{unknown}/import", headers=auth_user.headers
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_tc_476_destination_detail_for_curated_and_live(
    live: Live, auth_user: AuthUser, sampleton: Destination, db_session: AsyncSession
) -> None:
    curated = await live.client.get(f"{V1}/destinations/{sampleton.id}", headers=auth_user.headers)
    assert curated.status_code == 200
    body = curated.json()
    assert body["data_tier"] == "curated"
    assert body["import"] is None
    assert body["attribution"], "the SAMPLE places carry their sources"
    listed = await live.client.get(f"{V1}/destinations", headers=auth_user.headers)
    api_06_item = next(item for item in listed.json() if item["id"] == str(sampleton.id))
    assert {k: body[k] for k in api_06_item} == api_06_item

    resolved = await _resolve(live, auth_user)
    destination_id = uuid.UUID(resolved.json()["destination_id"])
    queued = await live.client.get(f"{V1}/destinations/{destination_id}", headers=auth_user.headers)
    assert queued.status_code == 200
    assert queued.json()["data_tier"] == "live"
    assert queued.json()["import"]["status"] == "queued"
    assert queued.json()["attribution"] == []
    assert "import_requested_by" not in queued.json()

    source = DataSource(
        name="OpenStreetMap",
        source_type="osm_import",
        licence="ODbL 1.0",
        attribution_text="Place data © OpenStreetMap contributors, available under the Open "
        "Database Licence (ODbL)",
        url="https://www.openstreetmap.org/copyright",
    )
    db_session.add(source)
    await db_session.flush()
    db_session.add(
        Place(
            destination_id=destination_id,
            source_id=source.id,
            external_ref=f"{LIVETON}:n1",
            name="Sample Museum (SAMPLE)",
            category="museum",
            tags=["history", "indoor"],
            lat=Decimal("23.500000"),
            lon=Decimal("77.500000"),
            typical_duration_min=90,
            price_label="unavailable",
            hours_label="unavailable",
            verification_status="imported_osm",
        )
    )
    await _complete(db_session, destination_id)
    await db_session.flush()
    completed = await live.client.get(
        f"{V1}/destinations/{destination_id}", headers=auth_user.headers
    )
    assert completed.json()["import"]["status"] == "completed"
    assert completed.json()["imported_at"] is not None
    assert completed.json()["attribution"] == [
        {
            "source_name": "OpenStreetMap",
            "licence": "ODbL 1.0",
            "attribution_text": "Place data © OpenStreetMap contributors, available under the "
            "Open Database Licence (ODbL)",
            "url": "https://www.openstreetmap.org/copyright",
        }
    ]


@pytest.mark.asyncio
async def test_tc_476_inactive_curated_destination_is_404(
    live: Live, auth_user: AuthUser, sampleton: Destination, db_session: AsyncSession
) -> None:
    await db_session.execute(
        update(Destination).where(Destination.id == sampleton.id).values(is_active=False)
    )
    response = await live.client.get(f"{V1}/destinations/{sampleton.id}", headers=auth_user.headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tc_476_api_06_lists_curated_destinations_only(
    live: Live, auth_user: AuthUser, sampleton: Destination, db_session: AsyncSession
) -> None:
    resolved = await _resolve(live, auth_user)
    destination_id = uuid.UUID(resolved.json()["destination_id"])
    await _complete(db_session, destination_id)
    listed = await live.client.get(f"{V1}/destinations", headers=auth_user.headers)
    ids = {item["id"] for item in listed.json()}
    assert str(sampleton.id) in ids
    assert str(destination_id) not in ids


@pytest.mark.asyncio
async def test_tc_476_routes_need_a_token(live: Live) -> None:
    for method, path in (
        ("GET", f"{V1}/destinations/search?q=liveton"),
        ("POST", f"{V1}/destinations/resolve"),
        ("GET", f"{V1}/destinations/{uuid.uuid4()}/import"),
        ("GET", f"{V1}/destinations/{uuid.uuid4()}"),
    ):
        response = await live.client.request(method, path, json={"osm_ref": LIVETON})
        assert response.status_code == 401, path


# ---------- TC-477 trip create ----------


def _trip(destination_id: uuid.UUID, currency: str) -> dict[str, Any]:
    start = date.today() + timedelta(days=30)
    return {
        "title": "Weekend in Liveton",
        "destination_id": str(destination_id),
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=1)).isoformat(),
        "adults": 2,
        "children": 0,
        "group_needs": [],
        "budget": {"amount": "15000.00", "currency": currency},
    }


@pytest.mark.asyncio
async def test_tc_477_trip_for_a_completed_live_destination_uses_its_currency(
    live: Live, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    resolved = await _resolve(live, auth_user)
    destination_id = uuid.UUID(resolved.json()["destination_id"])
    await _complete(db_session, destination_id)
    created = await live.client.post(
        f"{V1}/trips", json=_trip(destination_id, "INR"), headers=auth_user.headers
    )
    assert created.status_code == 201, created.text
    wrong_currency = await live.client.post(
        f"{V1}/trips", json=_trip(destination_id, "GBP"), headers=auth_user.headers
    )
    assert wrong_currency.status_code == 422


@pytest.mark.asyncio
async def test_tc_477_importing_destination_is_refused_listing_curated_only(
    live: Live, auth_user: AuthUser, sampleton: Destination, db_session: AsyncSession
) -> None:
    completed = await _resolve(live, auth_user, TINYHAM)
    await _complete(db_session, uuid.UUID(completed.json()["destination_id"]))
    importing = await _resolve(live, auth_user)
    importing_id = uuid.UUID(importing.json()["destination_id"])
    response = await live.client.post(
        f"{V1}/trips", json=_trip(importing_id, "INR"), headers=auth_user.headers
    )
    assert response.status_code == 422
    message = response.json()["error"]["details"][0]["message"]
    assert "Sampleton" in message
    assert "Liveton" not in message
    assert "Tinyham" not in message
