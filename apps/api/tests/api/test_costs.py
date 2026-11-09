"""API-33, API-34 and the saved item costs (§6.6.6, §9.3.1; IMP-308, IMP-411: TC-140, TC-223,
TC-224, FR-033, FR-071, FR-072, IMD-05).

TC-140 has no §13.3 row, so it follows the card's wording: stored totals equal the backend
calculation even when the model output carries its own total. io-1 has no total or price field and
refuses undeclared fields, so a model can only carry a total in its free text.
"""

import copy
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.ai import SAMPLE_OUTPUT
from fixtures.auth import AuthUser
from fixtures.db import insert_auth_user
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.budget import repository as budget_repository
from app.core.config import get_settings
from app.db.models import Destination, ItineraryItem, ItineraryWarning, Place, Trip
from app.generation import jobs
from app.places import seed
from app.schemas.ai import GenerationRequest, ItineraryOutput

SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"
MODEL_TOTAL = "Total cost: 1.00 GBP, every price is 0.00."
Job = tuple[uuid.UUID, ModelProvider]


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


@pytest.fixture
def queue(api_app: FastAPI) -> list[Job]:
    jobs_seen: list[Job] = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: jobs_seen.append((g, p))
    api_app.dependency_overrides[get_model_provider] = lambda: MockProvider("ok", app_env="test")
    return jobs_seen


async def create_trip(
    client: httpx.AsyncClient, user: AuthUser, destination: Destination, budget: str | None = None
) -> str:
    body: dict[str, Any] = {
        "title": "Weekend in Sampleton",
        "destination_id": str(destination.id),
        "start_date": "2026-12-04",
        "end_date": "2026-12-06",
        "adults": 2,
        "children": 1,
    }
    if budget:
        body["budget"] = {"amount": budget, "currency": "GBP"}
    created = await client.post("/api/v1/trips", json=body, headers=user.headers)
    assert created.status_code == 201, created.text
    trip_id: str = created.json()["id"]
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food"], "must_visit_place_ids": []},
        headers=user.headers,
    )
    assert saved.status_code == 200, saved.text
    return trip_id


async def generate(
    client: httpx.AsyncClient,
    session: AsyncSession,
    queue: list[Job],
    user: AuthUser,
    trip_id: str,
) -> None:
    await client.patch("/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers)
    started = await client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": "ai"}, headers=user.headers
    )
    assert started.status_code == 202, started.text

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    while queue:
        await jobs.run(*queue.pop(0), job_transaction)
    done = await client.get(f"/api/v1/generations/{started.json()['id']}", headers=user.headers)
    assert done.json()["status"] == "completed", done.text


async def costs(client: httpx.AsyncClient, user: AuthUser, trip_id: str) -> dict[str, Any]:
    answer = await client.get(f"/api/v1/trips/{trip_id}/costs", headers=user.headers)
    assert answer.status_code == 200, answer.text
    body: dict[str, Any] = answer.json()
    return body


async def items_with_places(
    session: AsyncSession, trip_id: str
) -> list[tuple[ItineraryItem, Place]]:
    rows = await session.execute(
        select(ItineraryItem, Place)
        .join(Place, Place.id == ItineraryItem.place_id)
        .where(ItineraryItem.trip_id == uuid.UUID(trip_id))
        .execution_options(populate_existing=True)
    )
    return [(item, place) for item, place in rows]


def dec(value: str) -> Decimal:
    return Decimal(value)


@pytest.mark.asyncio
async def test_costs_work_without_an_itinerary_from_traveller_inputs_only(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    await budget_repository.upsert_settings(
        db_session,
        uuid.UUID(trip_id),
        transport_allowance_per_day=Decimal("10.00"),
        stay_budget_per_night=Decimal("35.00"),
    )

    body = await costs(api_client, auth_user, trip_id)

    assert body["currency"] == "GBP"
    assert body["estimate"] == {"min": "100.00", "max": "100.00"}
    assert body["contingency"] == {"pct": 10, "amount": "10.00"}
    assert body["planning_total"] == "110.00"
    assert body["per_traveller"] == {
        "travellers": 3,
        "largest_share": "36.67",
        "label": "average",
    }
    assert body["budget"] == {"amount": None, "status": "none", "ratio_pct": None, "excess": None}
    assert (body["complete"], body["incomplete_items"], body["alerts"]) == (False, [], [])
    assert body["settings"] == {
        "transport_allowance_per_day": "10.00",
        "stay_budget_per_night": "35.00",
        "contingency_pct": 10,
    }


@pytest.mark.asyncio
async def test_saved_items_carry_costs_from_the_places_rows(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    queue: list[Job],
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)

    await generate(api_client, db_session, queue, auth_user, trip_id)

    rows = await items_with_places(db_session, trip_id)
    assert rows
    for item, place in rows:
        assert item.cost_currency == "GBP"
        if place.price_min is None:
            assert (item.cost_min, item.cost_max, item.cost_label) == (None, None, "unavailable")
            continue
        assert item.cost_label == place.price_label
        factor = Decimal("2.5") if "child_half" in place.tags else Decimal(3)
        factor = Decimal(2) if "child_free" in place.tags else factor
        assert item.cost_min == place.price_min * factor
        assert item.cost_max == (place.price_max or place.price_min) * factor


@pytest.mark.asyncio
async def test_tc_140_stored_totals_equal_the_calculation_when_the_model_writes_its_own(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    queue: list[Job],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_generate = MockProvider.generate_itinerary

    async def with_a_total(self: MockProvider, request: GenerationRequest) -> Any:
        result = await real_generate(self, request)
        result.output.summary = MODEL_TOTAL
        result.output.assumptions = [MODEL_TOTAL]
        result.output.days[0].items[0].note = MODEL_TOTAL
        return result

    monkeypatch.setattr(MockProvider, "generate_itinerary", with_a_total)
    trip_id = await create_trip(api_client, auth_user, sampleton)

    await generate(api_client, db_session, queue, auth_user, trip_id)

    rows = await items_with_places(db_session, trip_id)
    low = sum((item.cost_min or Decimal(0) for item, _ in rows), Decimal(0))
    high = sum((item.cost_max or Decimal(0) for item, _ in rows), Decimal(0))
    body = await costs(api_client, auth_user, trip_id)
    assert (dec(body["estimate"]["min"]), dec(body["estimate"]["max"])) == (low, high)
    assert dec(body["planning_total"]) == high + dec(body["contingency"]["amount"])
    assert body["planning_total"] != "1.00"
    itinerary = await api_client.get(
        f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers
    )
    totals = itinerary.json()["totals"]
    assert totals["estimate"] == body["estimate"]
    assert totals["planning_total"] == body["planning_total"]


@pytest.mark.parametrize("path", [("total",), ("days", 0, "items", 0, "price")])
def test_tc_140_a_total_or_price_field_is_refused_by_the_model_output_schema(
    path: tuple[Any, ...],
) -> None:
    answer = copy.deepcopy(SAMPLE_OUTPUT)
    target: Any = answer
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = "1.00"
    with pytest.raises(ValidationError):
        ItineraryOutput.model_validate(answer)


@pytest.mark.asyncio
async def test_a_price_in_another_currency_is_saved_unavailable_and_listed(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    queue: list[Job],
) -> None:
    await db_session.execute(
        update(Place)
        .where(Place.destination_id == sampleton.id, Place.price_min.is_not(None))
        .values(price_currency="EUR")
    )
    trip_id = await create_trip(api_client, auth_user, sampleton)

    await generate(api_client, db_session, queue, auth_user, trip_id)

    rows = await items_with_places(db_session, trip_id)
    assert {item.cost_label for item, _ in rows} == {"unavailable"}
    assert {item.cost_min for item, _ in rows} == {None}
    body = await costs(api_client, auth_user, trip_id)
    assert sorted(body["incomplete_items"]) == sorted(str(item.id) for item, _ in rows)
    assert (body["complete"], body["estimate"]["max"]) == (False, "0.00")


@pytest.mark.asyncio
async def test_the_tables_add_up_and_amounts_are_two_decimal_strings(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    queue: list[Job],
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    await budget_repository.upsert_settings(
        db_session, uuid.UUID(trip_id), transport_allowance_per_day=Decimal("7.77")
    )
    await generate(api_client, db_session, queue, auth_user, trip_id)

    body = await costs(api_client, auth_user, trip_id)

    total = dec(body["planning_total"])
    by_day = sum(dec(d["max"]) + dec(d["contingency_share"]) for d in body["by_day"])
    assert by_day == total
    assert sum(dec(line["max"]) for line in body["by_category"]) == total
    assert [d["day_number"] for d in body["by_day"]] == [1, 2, 3]
    assert all(len(d["contingency_share"].split(".")[1]) == 2 for d in body["by_day"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "status", "code", "has_excess"),
    [
        ("110.00", "near", "BUDGET_NEAR", False),
        ("100.00", "exceeded", "BUDGET_EXCEEDED", True),
        ("1000.00", "none", None, False),
    ],
)
async def test_f_3_budget_status_and_excess_through_the_api(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    amount: str,
    status: str,
    code: str | None,
    has_excess: bool,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton, budget=amount)
    await budget_repository.upsert_settings(
        db_session, uuid.UUID(trip_id), stay_budget_per_night=Decimal("50.00")
    )

    body = await costs(api_client, auth_user, trip_id)  # planning total 110.00

    assert body["budget"]["amount"] == amount
    assert body["budget"]["status"] == status
    assert body["budget"]["excess"] == ("10.00" if has_excess else None)
    assert [alert["code"] for alert in body["alerts"]] == ([code] if code else [])


@pytest.fixture
def switches_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("FEATURES_DISABLED", "contingency,budget_alerts")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_the_disabled_switches_drop_the_contingency_and_the_alerts(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    switches_off: None,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton, budget="100.00")
    await budget_repository.upsert_settings(
        db_session, uuid.UUID(trip_id), stay_budget_per_night=Decimal("60.00")
    )

    body = await costs(api_client, auth_user, trip_id)

    assert body["contingency"] == {"pct": 0, "amount": "0.00"}
    assert body["settings"]["contingency_pct"] == 10
    assert body["planning_total"] == "120.00"
    assert body["budget"]["status"] == "exceeded"
    assert body["alerts"] == []


@pytest.mark.asyncio
async def test_another_users_trip_and_a_missing_trip_are_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    other = AuthUser(user_id=await insert_auth_user(db_session), email="other@example.test")

    foreign = await api_client.get(f"/api/v1/trips/{trip_id}/costs", headers=other.headers)
    missing = await api_client.get(f"/api/v1/trips/{uuid.uuid4()}/costs", headers=auth_user.headers)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["error"]["code"] == missing.json()["error"]["code"] == "NOT_FOUND"


# API-34 (FR-072; IMP-411)


async def patch_budget_settings(
    client: httpx.AsyncClient, user: AuthUser, trip_id: str, body: dict[str, Any]
) -> httpx.Response:
    return await client.patch(
        f"/api/v1/trips/{trip_id}/budget-settings", json=body, headers=user.headers
    )


@pytest.mark.asyncio
async def test_tc_223_budget_settings_appear_as_traveller_input(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)  # 3 days, 2 nights

    response = await patch_budget_settings(
        api_client,
        auth_user,
        trip_id,
        {"transport_allowance_per_day": "10.00", "stay_budget_per_night": "35.00"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    lines = {line["category"]: line for line in body["by_category"]}
    assert lines["transport"] == {
        "category": "transport",
        "min": "30.00",
        "max": "30.00",
        "label": "traveller_input",
    }
    assert lines["accommodation"]["max"] == "70.00"
    assert lines["accommodation"]["label"] == "traveller_input"
    assert body["settings"]["transport_allowance_per_day"] == "10.00"
    assert body == await costs(api_client, auth_user, trip_id)


@pytest.mark.asyncio
async def test_tc_224_budget_settings_cleared_show_unavailable(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    await patch_budget_settings(
        api_client, auth_user, trip_id, {"transport_allowance_per_day": "10.00"}
    )

    response = await patch_budget_settings(
        api_client, auth_user, trip_id, {"transport_allowance_per_day": None}
    )

    assert response.status_code == 200, response.text
    lines = {line["category"]: line for line in response.json()["by_category"]}
    assert lines["transport"]["label"] == "unavailable"
    assert lines["accommodation"]["label"] == "unavailable"
    assert response.json()["settings"]["transport_allowance_per_day"] is None


@pytest.mark.asyncio
async def test_budget_settings_write_no_warnings_and_keep_the_plan_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    queue: list[Job],
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton, budget="10.00")
    await generate(api_client, db_session, queue, auth_user, trip_id)
    trip = uuid.UUID(trip_id)
    count = select(func.count()).where(ItineraryWarning.trip_id == trip)
    warnings_before = await db_session.scalar(count)
    revision_before = await db_session.scalar(select(Trip.plan_revision).where(Trip.id == trip))

    response = await patch_budget_settings(
        api_client, auth_user, trip_id, {"stay_budget_per_night": "500.00"}
    )

    assert response.status_code == 200, response.text
    assert [alert["code"] for alert in response.json()["alerts"]] == ["BUDGET_EXCEEDED"]
    assert await db_session.scalar(count) == warnings_before
    assert (
        await db_session.scalar(select(Trip.plan_revision).where(Trip.id == trip))
        == revision_before
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [{"transport_allowance_per_day": "-1.00"}, {"contingency_pct": 51}, {"unknown": "1.00"}],
)
async def test_budget_settings_refuse_invalid_values(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    sampleton: Destination,
    body: dict[str, Any],
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)

    response = await patch_budget_settings(api_client, auth_user, trip_id, body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_budget_settings_refuse_contingency_when_switched_off(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    sampleton: Destination,
    switches_off: None,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)

    response = await patch_budget_settings(api_client, auth_user, trip_id, {"contingency_pct": 5})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "contingency_pct"


@pytest.mark.asyncio
async def test_budget_settings_of_another_users_trip_are_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton)
    other = AuthUser(user_id=await insert_auth_user(db_session), email="other@example.test")

    response = await patch_budget_settings(
        api_client, other, trip_id, {"transport_allowance_per_day": "1.00"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    mine = await costs(api_client, auth_user, trip_id)
    assert mine["settings"]["transport_allowance_per_day"] is None
