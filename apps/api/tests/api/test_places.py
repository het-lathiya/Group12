"""API-06, API-16 and API-17 (§6.6.3, §6.5 Destination, PlaceSummary and PlaceOut; FR-019:
TC-069, TC-101, TC-102; IMP-205 places-api-search part; FR-016: TC-092 to TC-094, IMP-509
whole-task part; FR-017, FR-018: TC-095 to TC-098, IMP-604 search-api part).

Runs against the migrated test database with Sampleton loaded through the seed (IMP-107, IMP-205);
every test is rolled back.
"""

import uuid
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fixtures.auth import AuthUser
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataSource, Destination, Place, PlaceOpeningHours
from app.places import seed, vocabulary

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"

DESTINATION_FIELDS = {
    "id",
    "slug",
    "name",
    "region",
    "country_code",
    "timezone",
    "currency",
    "is_sample",
    "center",
    "bbox",
}
PLACE_FIELDS = {
    "id",
    "name",
    "category",
    "tags",
    "lat",
    "lon",
    "typical_duration_min",
    "price",
    "price_label",
    "hours_label",
    "verification_status",
    "suitability",
    "source_name",
    "distance_m",
}
SAMPLE_SOURCE = "SAMPLE fixture (synthetic)"


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


def destination_row(slug: str, name: str, *, active: bool = True) -> Destination:
    return Destination(
        slug=slug,
        name=name,
        country_code="GB",
        timezone="Europe/London",
        currency="GBP",
        center_lat=Decimal("53.9"),
        center_lon=Decimal("2.2"),
        bbox_min_lat=Decimal("53.8"),
        bbox_max_lat=Decimal("54.0"),
        bbox_min_lon=Decimal("2.1"),
        bbox_max_lon=Decimal("2.3"),
        is_active=active,
    )


async def add_destination_with_place(
    session: AsyncSession, sampleton: Destination, *, active: bool, place_name: str
) -> Destination:
    destination = destination_row(f"t-{uuid.uuid4().hex[:8]}", f"Test {place_name}", active=active)
    session.add(destination)
    await session.flush()
    source = await session.scalar(select(DataSource))
    assert source is not None
    session.add(
        Place(
            destination_id=destination.id,
            source_id=source.id,
            external_ref=f"other-{uuid.uuid4().hex[:8]}",
            name=place_name,
            category="sight",
            lat=Decimal("53.9"),
            lon=Decimal("2.2"),
            typical_duration_min=30,
        )
    )
    await session.flush()
    return destination


async def search(
    client: httpx.AsyncClient, user: AuthUser, destination: Destination, **params: Any
) -> httpx.Response:
    return await client.get(
        "/api/v1/places",
        params={"destination_id": str(destination.id), **params},
        headers=user.headers,
    )


# API-06


@pytest.mark.asyncio
async def test_destinations_lists_only_active_destinations_ordered_by_name(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    db_session.add_all(
        [
            destination_row(f"a-{uuid.uuid4().hex[:6]}", "Aardvark Bay (test)"),
            destination_row(f"z-{uuid.uuid4().hex[:6]}", "Zed Hidden (test)", active=False),
        ]
    )
    await db_session.flush()

    response = await api_client.get("/api/v1/destinations", headers=auth_user.headers)

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Zed Hidden (test)" not in names
    assert names == sorted(names)
    assert {"Aardvark Bay (test)", sampleton.name} <= set(names)


@pytest.mark.asyncio
async def test_tc_069_destinations_return_the_section_6_5_shape(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    response = await api_client.get("/api/v1/destinations", headers=auth_user.headers)
    [item] = [d for d in response.json() if d["slug"] == "sampleton"]

    assert set(item) == DESTINATION_FIELDS
    assert item == {
        "id": str(sampleton.id),
        "slug": "sampleton",
        "name": "Sampleton (sample)",
        "region": "Sample region (synthetic)",
        "country_code": "GB",
        "timezone": "Europe/London",
        "currency": "GBP",
        "is_sample": True,
        "center": {"lat": 53.9, "lon": 2.2},
        "bbox": {"min_lat": 53.85, "max_lat": 53.95, "min_lon": 2.1, "max_lon": 2.3},
    }


@pytest.mark.asyncio
async def test_destinations_and_places_need_a_token(api_client: httpx.AsyncClient) -> None:
    for path in ("/api/v1/destinations", f"/api/v1/places?destination_id={uuid.uuid4()}"):
        response = await api_client.get(path)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"


# API-16


@pytest.mark.asyncio
async def test_places_returns_a_page_of_the_destinations_active_places_by_name(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    response = await search(api_client, auth_user, sampleton)

    assert response.status_code == 200
    page = response.json()
    assert (page["total"], page["limit"], page["offset"]) == (30, 20, 0)
    assert len(page["items"]) == 20
    assert all(set(item) == PLACE_FIELDS for item in page["items"])
    names = [item["name"] for item in page["items"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_places_pages_with_limit_and_offset(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    first = (await search(api_client, auth_user, sampleton, limit=25)).json()
    rest = (await search(api_client, auth_user, sampleton, limit=25, offset=25)).json()

    assert (len(first["items"]), len(rest["items"])) == (25, 5)
    ids = [item["id"] for item in first["items"] + rest["items"]]
    assert len(set(ids)) == 30


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": 51}, "limit"),
        ({"limit": 0}, "limit"),
        ({"offset": -1}, "offset"),
        ({"q": "x" * 81}, "q"),
        ({"category": "beach"}, "category.0"),
        ({"category": "stay"}, "category.0"),
    ],
    ids=["limit above 50", "limit 0", "negative offset", "q too long", "unknown", "stay"],
)
async def test_places_rejects_bad_query_values(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    sampleton: Destination,
    params: dict[str, Any],
    field: str,
) -> None:
    response = await search(api_client, auth_user, sampleton, **params)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == [field]


@pytest.mark.asyncio
async def test_places_needs_a_destination_id(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.get("/api/v1/places", headers=auth_user.headers)
    assert response.status_code == 422
    assert [d["field"] for d in response.json()["error"]["details"]] == ["destination_id"]


@pytest.mark.asyncio
async def test_places_filters_by_name_case_insensitively(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    page = (await search(api_client, auth_user, sampleton, q="harbour LOOKOUT")).json()
    assert [item["name"] for item in page["items"]] == ["Sample Harbour Lookout (sample)"]
    assert page["total"] == 1

    # LIKE wildcards in q are plain characters.
    wildcard = (await search(api_client, auth_user, sampleton, q="%")).json()
    assert wildcard == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.asyncio
async def test_places_filters_by_one_or_more_categories(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    food = (await search(api_client, auth_user, sampleton, category="food", limit=50)).json()
    assert food["total"] == 6
    assert {item["category"] for item in food["items"]} == {"food"}

    both = (
        await search(api_client, auth_user, sampleton, category=["food", "museum"], limit=50)
    ).json()
    assert both["total"] == 10
    assert {item["category"] for item in both["items"]} == {"food", "museum"}

    combined = (await search(api_client, auth_user, sampleton, category="food", q="zzz")).json()
    assert combined["total"] == 0  # an empty page is valid


@pytest.mark.asyncio
async def test_places_hides_inactive_places_and_other_destinations(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    await db_session.execute(
        update(Place).where(Place.external_ref == "sample-001").values(is_active=False)
    )
    other = await add_destination_with_place(
        db_session, sampleton, active=True, place_name="Elsewhere Tower"
    )

    page = (await search(api_client, auth_user, sampleton, limit=50)).json()
    names = {item["name"] for item in page["items"]}
    assert page["total"] == 29
    assert "Sample Harbour Lookout (sample)" not in names
    assert "Elsewhere Tower" not in names

    theirs = (await search(api_client, auth_user, other)).json()
    assert [item["name"] for item in theirs["items"]] == ["Elsewhere Tower"]


@pytest.mark.asyncio
async def test_places_of_an_inactive_or_unknown_destination_are_404(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    hidden = await add_destination_with_place(
        db_session, sampleton, active=False, place_name="Hidden Tower"
    )
    inactive = await search(api_client, auth_user, hidden)
    unknown = await api_client.get(
        "/api/v1/places", params={"destination_id": str(uuid.uuid4())}, headers=auth_user.headers
    )
    # IMD-127, §6.2: an inactive destination is invisible, identical to an unknown one.
    for response in (inactive, unknown):
        assert response.status_code == 404
        error = response.json()["error"]
        assert (error["code"], error["message"]) == ("NOT_FOUND", "Not found.")
    assert inactive.json()["error"]["details"] == unknown.json()["error"]["details"]


@pytest.mark.asyncio
async def test_tc_101_tc_102_tags_from_the_vocabulary_and_unknown_suitability_as_null(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    items = (await search(api_client, auth_user, sampleton, limit=50)).json()["items"]
    by_name = {item["name"]: item for item in items}

    assert all(set(item["tags"]) <= vocabulary.TAGS for item in items)
    lookout = by_name["Sample Harbour Lookout (sample)"]  # sample-001
    assert set(lookout["tags"]) == {"views", "outdoor"}
    assert lookout["suitability"] == {"step_free": True, "child_friendly": True, "indoor": False}
    tower = by_name["Sample Old Signal Tower (sample)"]  # sample-002: step_free left empty
    assert tower["suitability"]["step_free"] is None  # unknown, never false


@pytest.mark.asyncio
async def test_places_show_prices_as_money_and_null_when_unpriced(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    items = (await search(api_client, auth_user, sampleton, q="Signal Tower")).json()["items"]
    [tower] = items
    assert tower["price"] == {"min": "3.00", "max": "5.00", "currency": "GBP", "label": "estimate"}
    assert (tower["lat"], tower["lon"]) == (53.876, 2.12)
    assert tower["verification_status"] == "estimated"

    page = (await search(api_client, auth_user, sampleton, limit=50)).json()
    unpriced = [item for item in page["items"] if item["price_label"] == "unavailable"]
    assert unpriced
    assert all(item["price"] is None for item in unpriced)


# API-16 for the explore page (IMP-509; FR-016). `make test-api ARGS='-k places_list'`.


@pytest.mark.asyncio
async def test_tc_092_places_list_pages_every_active_place_once_by_name_then_id(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    pages = [
        (await search(api_client, auth_user, sampleton, limit=12, offset=offset)).json()
        for offset in (0, 12, 24)
    ]

    assert [len(page["items"]) for page in pages] == [12, 12, 6]
    assert {page["total"] for page in pages} == {30}
    items = [item for page in pages for item in page["items"]]
    assert len({item["id"] for item in items}) == 30
    keys = [(item["name"], item["id"]) for item in items]
    assert keys == sorted(keys)
    beyond = (await search(api_client, auth_user, sampleton, offset=30)).json()
    assert (beyond["items"], beyond["total"]) == ([], 30)


@pytest.mark.asyncio
async def test_tc_093_places_list_names_the_source_and_verification_of_every_place(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    items = (await search(api_client, auth_user, sampleton, limit=50)).json()["items"]

    assert len(items) == 30
    assert {item["source_name"] for item in items} == {SAMPLE_SOURCE}
    assert all(item["verification_status"] in vocabulary.VERIFICATION_STATUSES for item in items)


@pytest.mark.asyncio
async def test_tc_094_places_list_labels_sample_prices_and_hours_as_estimates(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    items = (await search(api_client, auth_user, sampleton, limit=50)).json()["items"]

    # The explore page shows the sample banner from these labels and API-10's is_sample.
    assert all(item["price_label"] != "curated" for item in items)
    assert all(item["hours_label"] != "curated" for item in items)
    lookout = next(i for i in items if i["name"] == "Sample Harbour Lookout (sample)")
    assert (lookout["price_label"], lookout["verification_status"]) == ("estimate", "estimated")


@pytest.mark.asyncio
async def test_places_list_rejects_limit_51_and_needs_a_token(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    too_many = await search(api_client, auth_user, sampleton, limit=51)
    assert too_many.status_code == 422
    assert too_many.json()["error"]["code"] == "VALIDATION_ERROR"

    anonymous = await api_client.get("/api/v1/places", params={"destination_id": str(sampleton.id)})
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_places_list_keeps_to_one_destination_and_hides_inactive_rows(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    other = await add_destination_with_place(
        db_session, sampleton, active=True, place_name="Aaa Elsewhere Gate"
    )
    await db_session.execute(
        update(Place).where(Place.external_ref == "sample-002").values(is_active=False)
    )

    first = (await search(api_client, auth_user, sampleton, limit=1)).json()
    assert first["total"] == 29
    assert first["items"][0]["name"] != "Aaa Elsewhere Gate"
    every = (await search(api_client, auth_user, sampleton, limit=50)).json()["items"]
    names = {item["name"] for item in every}
    assert "Sample Old Signal Tower (sample)" not in names
    assert "Aaa Elsewhere Gate" not in names

    theirs = (await search(api_client, auth_user, other)).json()
    [elsewhere] = theirs["items"]
    assert elsewhere["name"] == "Aaa Elsewhere Gate"
    assert elsewhere["source_name"]


# API-16 filters and API-17 detail (IMP-604; FR-017, FR-018).
# `make test-api ARGS='-k "filter or place_detail"'`.


async def names(
    client: httpx.AsyncClient, user: AuthUser, destination: Destination, **params: Any
) -> list[str]:
    response = await search(client, user, destination, limit=50, **params)
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


def refs(*numbers: int) -> set[str]:
    return {f"sample-{n:03d}" for n in numbers}


async def names_of(session: AsyncSession, external_refs: set[str]) -> list[str]:
    rows = await session.scalars(select(Place.name).where(Place.external_ref.in_(external_refs)))
    return sorted(rows.all())


@pytest.mark.asyncio
async def test_tc_095_filter_by_category_and_price_band_returns_only_matching_places(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    found = await names(api_client, auth_user, sampleton, category="food", price_max="7.00")
    # Lowest prices 3.00, 7.00 and 4.00; the unpriced sample-017 never matches a price filter.
    assert found == await names_of(db_session, refs(13, 16, 18))
    items = (await search(api_client, auth_user, sampleton, price_max="7", limit=50)).json()
    assert all(Decimal(i["price"]["min"]) <= 7 for i in items["items"])


@pytest.mark.asyncio
async def test_filter_by_interest_tag_duration_and_step_free(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    lunch = await names(api_client, auth_user, sampleton, interest="lunch")
    assert lunch == await names_of(db_session, refs(14, 16, 17))
    either = await names(api_client, auth_user, sampleton, interest=["lunch", "wildlife"])
    assert either == await names_of(db_session, refs(11, 14, 16, 17))
    short = await names(api_client, auth_user, sampleton, duration_max_min=30)
    assert short == await names_of(db_session, refs(3, 4, 13, 18, 20, 21, 25))
    # Unknown step-free (NULL) is not step-free; false is no filter.
    assert await names(api_client, auth_user, sampleton, step_free="true") == await names_of(
        db_session, refs(1, 5)
    )
    assert len(await names(api_client, auth_user, sampleton, step_free="false")) == 30


@pytest.mark.asyncio
async def test_filter_q_matches_a_tag_as_well_as_the_name(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    assert await names(api_client, auth_user, sampleton, q="WILDLIFE") == [
        "Sample Heron Marsh (sample)"
    ]


@pytest.mark.asyncio
async def test_tc_096_filter_without_a_match_is_an_empty_page_with_total_0(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    response = await search(
        api_client, auth_user, sampleton, category="museum", step_free="true", price_max="1.00"
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.asyncio
async def test_tc_097_filter_near_a_point_orders_by_distance(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    near = {"near_lat": "53.86", "near_lon": "2.3"}  # sample-030, Sample Climbing Wall
    page = (await search(api_client, auth_user, sampleton, limit=50, **near)).json()

    distances = [item["distance_m"] for item in page["items"]]
    assert page["total"] == 30
    assert page["items"][0]["name"] == "Sample Climbing Wall (sample)"
    assert distances[0] == 0
    assert distances == sorted(distances)
    assert all(isinstance(d, int) for d in distances)

    close = (await search(api_client, auth_user, sampleton, max_distance_m=3000, **near)).json()
    assert 0 < close["total"] < 30
    assert all(item["distance_m"] <= 3000 for item in close["items"])
    # Without a point there is no distance.
    plain = (await search(api_client, auth_user, sampleton)).json()
    assert {item["distance_m"] for item in plain["items"]} == {None}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "fields"),
    [
        ({"tag": "views"}, ["tag"]),
        ({"price": "3", "sort": "x"}, ["price", "sort"]),
        ({"near_lat": "53.86"}, ["near_lon"]),
        ({"near_lon": "2.3"}, ["near_lat"]),
        ({"max_distance_m": "500"}, ["max_distance_m"]),
        ({"interest": "beach"}, ["interest.0"]),
        ({"price_max": "1.234"}, ["price_max"]),
        ({"price_max": "-1"}, ["price_max"]),
        ({"duration_max_min": "10"}, ["duration_max_min"]),
    ],
    ids=[
        "unknown param",
        "two unknown params",
        "lat without lon",
        "lon without lat",
        "distance without point",
        "unknown interest",
        "three decimals",
        "negative price",
        "duration below 15",
    ],
)
async def test_filter_rejects_unknown_or_bad_params_with_422(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    sampleton: Destination,
    params: dict[str, Any],
    fields: list[str],
) -> None:
    response = await search(api_client, auth_user, sampleton, **params)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == fields


async def curated_place(session: AsyncSession, destination: Destination) -> Place:
    source = await session.scalar(select(DataSource))
    assert source is not None
    place = Place(
        destination_id=destination.id,
        source_id=source.id,
        external_ref=f"curated-{uuid.uuid4().hex[:8]}",
        name="Curated Test Hall",
        category="museum",
        tags=["history"],
        description="A hall used by the detail test.",
        address="1 Test Row",
        lat=Decimal("53.9"),
        lon=Decimal("2.2"),
        typical_duration_min=60,
        price_min=Decimal("4.50"),
        price_max=Decimal("6.00"),
        price_currency="GBP",
        price_label="curated",
        hours_label="curated",
        hours_checked_on=date(2026, 10, 1),
        verification_status="curated_checked",
        step_free=True,
        website_url="https://example.test/hall",
    )
    session.add(place)
    await session.flush()
    session.add_all(
        [
            PlaceOpeningHours(
                place_id=place.id, weekday=1, is_closed=True, open_time=None, close_time=None
            ),
            PlaceOpeningHours(
                place_id=place.id,
                weekday=5,
                open_time=time(18, 0),
                close_time=time(1, 30),
                closes_next_day=True,
            ),
            PlaceOpeningHours(
                place_id=place.id, weekday=2, open_time=time(9, 0), close_time=time(17, 0)
            ),
        ]
    )
    await session.flush()
    return place


async def detail(client: httpx.AsyncClient, user: AuthUser, place_id: object) -> httpx.Response:
    return await client.get(f"/api/v1/places/{place_id}", headers=user.headers)


@pytest.mark.asyncio
async def test_tc_098_place_detail_has_curated_hours_with_checked_date_and_its_source(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    place = await curated_place(db_session, sampleton)

    response = await detail(api_client, auth_user, place.id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == PLACE_FIELDS | {
        "description",
        "address",
        "website_url",
        "booking_url",
        "hours",
        "hours_checked_on",
        "source",
        "saved",
        "must_visit",
    }
    assert (body["hours_label"], body["hours_checked_on"]) == ("curated", "2026-10-01")
    assert body["hours"] == [
        {
            "weekday": 1,
            "is_closed": True,
            "open_time": None,
            "close_time": None,
            "closes_next_day": False,
        },
        {
            "weekday": 2,
            "is_closed": False,
            "open_time": "09:00",
            "close_time": "17:00",
            "closes_next_day": False,
        },
        {
            "weekday": 5,
            "is_closed": False,
            "open_time": "18:00",
            "close_time": "01:30",
            "closes_next_day": True,
        },
    ]
    assert body["price"] == {"min": "4.50", "max": "6.00", "currency": "GBP", "label": "curated"}
    assert body["suitability"] == {"step_free": True, "child_friendly": None, "indoor": None}
    assert body["source"] == {
        "name": SAMPLE_SOURCE,
        "source_type": "other",
        "licence": "synthetic test data",
        "attribution_text": "Synthetic SAMPLE data for automated tests; not a real place.",
        "url": None,
        "retrieved_on": "2026-10-31",
    }
    assert (body["description"], body["address"]) == (
        "A hall used by the detail test.",
        "1 Test Row",
    )
    assert (body["saved"], body["must_visit"], body["distance_m"]) == (None, None, None)


@pytest.mark.asyncio
async def test_place_detail_never_fills_missing_hours_or_prices(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    by_ref = {
        p.external_ref: p.id
        for p in await db_session.scalars(
            select(Place).where(Place.external_ref.in_(["sample-003", "sample-007"]))
        )
    }
    no_hours = (await detail(api_client, auth_user, by_ref["sample-003"])).json()
    assert (no_hours["hours_label"], no_hours["hours"]) == ("unavailable", [])
    assert no_hours["hours_checked_on"] is None

    no_price = (await detail(api_client, auth_user, by_ref["sample-007"])).json()
    assert (no_price["price"], no_price["price_label"]) == (None, "unavailable")
    assert no_price["hours_label"] == "estimate"
    assert len(no_price["hours"]) == 7


@pytest.mark.asyncio
async def test_place_detail_of_an_inactive_or_unknown_place_is_404(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    await db_session.execute(
        update(Place).where(Place.external_ref == "sample-001").values(is_active=False)
    )
    inactive_id = await db_session.scalar(
        select(Place.id).where(Place.external_ref == "sample-001")
    )
    hidden = await add_destination_with_place(
        db_session, sampleton, active=False, place_name="Hidden Hall"
    )
    hidden_place = await db_session.scalar(
        select(Place.id).where(Place.destination_id == hidden.id)
    )

    for place_id in (inactive_id, hidden_place, uuid.uuid4()):
        response = await detail(api_client, auth_user, place_id)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
    anonymous = await api_client.get(f"/api/v1/places/{uuid.uuid4()}")
    assert anonymous.status_code == 401
