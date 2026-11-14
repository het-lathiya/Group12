"""Group the shortlist into geographically compact days (§8.9, FR-030; IMP-503).

Pure and deterministic: the same input gives identical ``day_hints``. One seed per day by
farthest-point seeding, must-visit places first, then the rest of the shortlist; each remaining
place, must-visit first and then in descending score (shortlist order), goes to the day with room
(fewer than the pace maximum of items) whose centroid is nearest by haversine distance. Ties
break on place_id for seeds and on day number for days. A place that finds no room is left out.
"""

from collections.abc import Sequence
from uuid import UUID

from app.routing.estimate import haversine_m
from app.schemas.ai import DayHint, ShortlistPlace


def _distance(place: ShortlistPlace, lat: float, lon: float) -> float:
    return haversine_m(place.lat, place.lon, lat, lon)


def group_days(
    shortlist: Sequence[ShortlistPlace],
    must_visit: Sequence[UUID],
    num_days: int,
    max_items: int,
) -> list[DayHint]:
    """``shortlist`` is in rank order, best first; the result has one hint per non-empty day."""
    must = set(must_visit)
    pool = [p for p in shortlist if p.place_id in must] + [
        p for p in shortlist if p.place_id not in must
    ]
    seeds: list[ShortlistPlace] = []
    for _ in range(min(num_days, len(pool))):
        seeded = {s.place_id for s in seeds}
        rest = [p for p in pool if p.place_id not in seeded]
        musts = [p for p in rest if p.place_id in must]
        candidates = musts or rest
        if not seeds:
            seeds.append(candidates[0])
            continue
        seeds.append(
            max(
                candidates,
                key=lambda p: (min(_distance(p, s.lat, s.lon) for s in seeds), -p.place_id.int),
            )
        )

    days = [[seed] for seed in seeds]
    seeded = {s.place_id for s in seeds}
    for place in (p for p in pool if p.place_id not in seeded):
        open_days = [i for i, day in enumerate(days) if len(day) < max_items]
        if not open_days:
            continue
        nearest = min(
            open_days,
            key=lambda i: (
                _distance(
                    place,
                    sum(p.lat for p in days[i]) / len(days[i]),
                    sum(p.lon for p in days[i]) / len(days[i]),
                ),
                i,
            ),
        )
        days[nearest].append(place)
    return [
        DayHint(day_number=number, place_ids=[p.place_id for p in day])
        for number, day in enumerate(days, 1)
    ]
