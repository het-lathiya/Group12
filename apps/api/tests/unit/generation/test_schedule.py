"""Schedule recalculation (§9.3.3, §9.3.5; FR-033, TC-139, IMP-308)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.generation import schedule
from app.routing.estimate import TravelEstimate, TravelMode, TravelSource
from app.schemas.ai import ItineraryDayOutput


@dataclass(frozen=True)
class Stop:
    id: UUID
    lat: float
    lon: float
    typical_duration_min: int


class Routes:
    """Each leg takes ``minutes`` from ``source``; the legs asked for are noted."""

    def __init__(self, minutes: int = 20, source: TravelSource = "routing_api") -> None:
        self.minutes = minutes
        self.source: TravelSource = source
        self.legs: list[tuple[UUID, UUID, str]] = []

    async def travel(self, origin: Any, target: Any, mode: TravelMode | str) -> TravelEstimate:
        self.legs.append((origin.id, target.id, str(mode)))
        return TravelEstimate(self.minutes, 1500, TravelMode(mode), self.source)


def stops(*durations: int) -> dict[str, Stop]:
    made = [Stop(uuid4(), 53.9, 2.2, duration) for duration in durations]
    return {str(stop.id): stop for stop in made}


def day(places: dict[str, Stop], number: int = 1, start: str = "07:13") -> ItineraryDayOutput:
    """A model's day: its times and durations are nonsense on purpose."""
    return ItineraryDayOutput.model_validate(
        {
            "day_number": number,
            "theme": "A theme",
            "items": [
                {
                    "place_id": place_id,
                    "start_time": start,
                    "duration_min": 15,
                    "slot_type": "activity",
                    "note": "A note",
                }
                for place_id in places
            ],
        }
    )


async def run(days: Sequence[ItineraryDayOutput], places: dict[str, Stop], routes: Routes) -> Any:
    return await schedule.recalculate(days, places, routes, "balanced", mode="walking")


@pytest.mark.asyncio
async def test_tc_139_model_times_and_durations_are_replaced_by_the_calculation() -> None:
    places = stops(60, 90, 30)

    [planned] = await run([day(places)], places, Routes(minutes=20))

    # 09:00 + 60 = 10:00, + 20 travel + 5 buffer; 10:25 + 90 = 11:55, + 25.
    assert [item.start_time for item in planned.items] == ["09:00", "10:25", "12:20"]
    assert [item.duration_min for item in planned.items] == [60, 90, 30]


@pytest.mark.asyncio
async def test_a_fallback_estimate_gets_the_larger_buffer() -> None:
    places = stops(60, 60)

    [planned] = await run([day(places)], places, Routes(20, "fallback_estimate"))

    assert planned.items[1].start_time == "10:35"  # 10:00 + 20 + 15


@pytest.mark.asyncio
async def test_the_travel_fields_are_stored_and_the_first_item_has_none() -> None:
    places = stops(60, 60)

    [planned] = await run([day(places)], places, Routes(20))

    first, second = planned.items
    assert first.travel_from_prev_min is None
    assert first.travel_source is None
    assert (
        second.travel_from_prev_min,
        second.travel_from_prev_m,
        second.travel_mode,
        second.travel_source,
    ) == (20, 1500, "walking", "routing_api")


@pytest.mark.asyncio
async def test_items_keep_the_models_order_and_each_leg_is_routed_in_it() -> None:
    places = stops(60, 60, 60)
    ids = [stop.id for stop in places.values()]
    routes = Routes()

    [planned] = await run([day(places)], places, routes)

    assert [item.place_id for item in planned.items] == list(places)
    assert routes.legs == [(ids[0], ids[1], "walking"), (ids[1], ids[2], "walking")]


@pytest.mark.asyncio
async def test_each_day_starts_again_at_nine_and_days_come_back_in_order() -> None:
    first, second = stops(60, 60), stops(45)
    routes = Routes()

    planned = await run([day(second, 2), day(first, 1)], first | second, routes)

    assert [d.day_number for d in planned] == [1, 2]
    assert planned[1].items[0].start_time == "09:00"
    assert planned[1].items[0].travel_source is None
    assert len(routes.legs) == 1  # no leg between the two days


@pytest.mark.asyncio
async def test_slot_type_theme_and_note_pass_through() -> None:
    places = stops(60)

    [planned] = await run([day(places)], places, Routes())

    assert planned.theme == "A theme"
    assert (planned.items[0].slot_type, planned.items[0].note) == ("activity", "A note")


@pytest.mark.asyncio
async def test_a_day_past_midnight_stops_at_the_last_minute() -> None:
    places = stops(480, 480, 480)

    [planned] = await run([day(places)], places, Routes(20))

    assert [item.start_time for item in planned.items] == ["09:00", "17:25", "23:59"]


@pytest.mark.asyncio
async def test_only_the_number_of_differences_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    places = stops(60, 60)
    model_day = day(places, start="09:00")

    with caplog.at_level(logging.INFO):
        await run([model_day], places, Routes())

    assert "on 2 items" in caplog.text  # the first differs in duration, the second in both
    assert "A note" not in caplog.text
    assert not any(place_id in caplog.text for place_id in places)
