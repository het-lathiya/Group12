"""The budget engine, BF-01 to BF-12 (§9.3.1; FR-033, FR-071, IMD-05, IMP-308). Pure: no I/O.

Amounts are integers in minor units; rounding is half-up, once per line formula, and sums add
integers only. ``to_minor`` and ``from_minor`` are the only conversions. No currency conversion: a
price in another currency is Unavailable. Zero is a real price; None is Unavailable.

Operator rulings B1 to B6 (RUN-049.2), pending their entry in the decision register:
- B1: the contingency is split evenly across the days, earlier days taking the extra minor unit.
- B2: place category food is food; shopping and stay are other; the rest are activities.
- B3: a null price_max means a_hi = a_lo.
- B4: ratio_pct is rounded half-up once to an integer; the contingency percentage is an integer.
- B5: the contingency row of the category table has min = max = C and label ``estimate``.
- B6: no category estimates exist, so a missing price is 0, listed and COST_INCOMPLETE;
  ESTIMATE_USED is not emitted until estimate data exists.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal, Protocol
from uuid import UUID

BUDGET_NEAR_PCT: Final = 90  # IMD-29
FOOD: Final = "food"
OTHER_CATEGORIES: Final = frozenset({"shopping", "stay"})
UNAVAILABLE: Final = "unavailable"
TAG_PER_GROUP: Final = "price_per_group"
TAG_CHILD_FREE: Final = "child_free"
TAG_CHILD_HALF: Final = "child_half"

ItemLabel = Literal["curated", "estimate", "unavailable"]
LineLabel = Literal["curated", "estimate", "unavailable", "traveller_input"]
LineCategory = Literal["activities", "food", "transport", "accommodation", "other", "contingency"]
BudgetState = Literal["none", "near", "exceeded"]
AlertCode = Literal["BUDGET_NEAR", "BUDGET_EXCEEDED", "COST_INCOMPLETE"]


class PricedPlace(Protocol):
    """What the engine reads from a ``places`` row."""

    @property
    def price_min(self) -> Decimal | None: ...
    @property
    def price_max(self) -> Decimal | None: ...
    @property
    def price_currency(self) -> str | None: ...
    @property
    def price_label(self) -> str: ...
    @property
    def tags(self) -> list[str]: ...


@dataclass(frozen=True)
class ItemCost:
    lo: int | None
    hi: int | None
    label: str


ITEM_UNAVAILABLE: Final = ItemCost(None, None, UNAVAILABLE)


@dataclass(frozen=True)
class CostedItem:
    """A plan item with its stored cost; ``lo`` and ``hi`` are None when it is Unavailable."""

    item_id: UUID
    day_number: int
    place_category: str
    lo: int | None
    hi: int | None
    label: str


@dataclass(frozen=True)
class CostInputs:
    num_days: int
    adults: int
    children: int
    currency: str
    budget: int | None
    transport_per_day: int | None
    stay_per_night: int | None
    contingency_pct: int


@dataclass(frozen=True)
class DayLine:
    day_number: int
    lo: int
    hi: int
    contingency_share: int


@dataclass(frozen=True)
class CategoryLine:
    category: LineCategory
    lo: int
    hi: int
    label: LineLabel


@dataclass(frozen=True)
class Alert:
    code: AlertCode
    severity: Literal["info", "warning"]
    message: str


@dataclass(frozen=True)
class CostSummary:
    estimate_lo: int
    estimate_hi: int
    contingency: int
    planning_total: int
    travellers: int
    largest_share: int
    status: BudgetState
    ratio_pct: int | None
    excess: int | None
    by_day: list[DayLine]
    by_category: list[CategoryLine]
    alerts: list[Alert]
    incomplete_items: list[UUID]
    complete: bool


def to_minor(amount: Decimal) -> int:
    return int(amount.scaleb(2))


def from_minor(minor: int) -> Decimal:
    return Decimal(minor).scaleb(-2)


def half_up(numerator: int, denominator: int) -> int:
    """numerator ÷ denominator rounded half-up, for non-negative integers."""
    return (2 * numerator + denominator) // (2 * denominator)


def split(total: int, parts: int) -> list[int]:
    """BF-10: q = floor(total / parts), r = total mod parts; the first r shares are q + 1."""
    share, remainder = divmod(total, parts)
    return [share + 1] * remainder + [share] * (parts - remainder)


def item_cost(place: PricedPlace, *, adults: int, children: int, currency: str) -> ItemCost:
    """BF-01 to BF-04: the group's cost of one visit, in the trip's currency."""
    if (
        place.price_min is None
        or place.price_currency != currency
        or place.price_label == UNAVAILABLE
    ):
        return ITEM_UNAVAILABLE
    a_lo = to_minor(place.price_min)
    a_hi = a_lo if place.price_max is None else to_minor(place.price_max)
    if TAG_PER_GROUP in place.tags:
        return ItemCost(a_lo, a_hi, place.price_label)
    # f in halves: 0, 0.5 or 1, so round(K·f·a) stays in integers.
    halves = 0 if TAG_CHILD_FREE in place.tags else 1 if TAG_CHILD_HALF in place.tags else 2

    def group(price: int) -> int:
        return adults * price + half_up(children * halves * price, 2)

    return ItemCost(group(a_lo), group(a_hi), place.price_label)


def cost_category(place_category: str) -> LineCategory:
    if place_category == FOOD:
        return "food"
    return "other" if place_category in OTHER_CATEGORIES else "activities"


def _items_label(labels: Sequence[str]) -> LineLabel:
    """The weakest label of a category's items; an empty category is an estimate of nothing."""
    if labels and all(label == UNAVAILABLE for label in labels):
        return "unavailable"
    return "curated" if labels and all(label == "curated" for label in labels) else "estimate"


def _input_line(category: LineCategory, amount: int | None) -> CategoryLine:
    if amount is None:
        return CategoryLine(category, 0, 0, "unavailable")
    return CategoryLine(category, amount, amount, "traveller_input")


def _status(
    total: int, budget: int | None, currency: str
) -> tuple[BudgetState, int | None, int | None, list[Alert]]:
    """BF-11: status, ratio_pct, excess and the alert. Exactly on budget is near, not exceeded."""
    if not budget:
        return "none", None, None, []
    ratio = half_up(100 * total, budget)
    if total > budget:
        excess = total - budget
        message = f"The plan is over your budget by {from_minor(excess):.2f} {currency}."
        return "exceeded", ratio, excess, [Alert("BUDGET_EXCEEDED", "warning", message)]
    if 100 * total >= BUDGET_NEAR_PCT * budget:
        message = f"The plan uses {ratio}% of your budget."
        return "near", ratio, None, [Alert("BUDGET_NEAR", "info", message)]
    return "none", ratio, None, []


def compute_costs(items: Iterable[CostedItem], inputs: CostInputs) -> CostSummary:
    """BF-05 to BF-12 over stored item costs and the traveller's inputs."""
    rows = list(items)
    nights = inputs.num_days - 1
    transport = (
        None if inputs.transport_per_day is None else inputs.num_days * inputs.transport_per_day
    )
    stay = None if inputs.stay_per_night is None else nights * inputs.stay_per_night
    lines = (transport or 0) + (stay or 0)

    estimate_lo = sum(row.lo or 0 for row in rows) + lines
    estimate_hi = sum(row.hi or 0 for row in rows) + lines
    contingency = half_up(estimate_hi * inputs.contingency_pct, 100)
    total = estimate_hi + contingency
    travellers = inputs.adults + inputs.children
    status, ratio, excess, alerts = _status(total, inputs.budget, inputs.currency)

    # A stale plan can hold days past the trip's new end; they still count towards the total.
    days = sorted({*range(1, inputs.num_days + 1), *(row.day_number for row in rows)})
    by_day = []
    for day, share in zip(days, split(contingency, len(days)), strict=True):
        allowance = 0
        if day <= inputs.num_days:
            allowance += inputs.transport_per_day or 0
        if day <= nights:
            allowance += inputs.stay_per_night or 0
        on_day = [row for row in rows if row.day_number == day]
        by_day.append(
            DayLine(
                day,
                sum(row.lo or 0 for row in on_day) + allowance,
                sum(row.hi or 0 for row in on_day) + allowance,
                share,
            )
        )

    by_category = []
    item_categories: tuple[LineCategory, ...] = ("activities", "food", "other")
    for category in item_categories:
        in_category = [row for row in rows if cost_category(row.place_category) == category]
        by_category.append(
            CategoryLine(
                category,
                sum(row.lo or 0 for row in in_category),
                sum(row.hi or 0 for row in in_category),
                _items_label([row.label for row in in_category]),
            )
        )
    by_category += [
        _input_line("transport", transport),
        _input_line("accommodation", stay),
        CategoryLine("contingency", contingency, contingency, "estimate"),
    ]

    incomplete = [row.item_id for row in rows if row.lo is None]
    if incomplete:
        message = f"{len(incomplete)} planned items have no price, so the total is incomplete."
        alerts = [*alerts, Alert("COST_INCOMPLETE", "warning", message)]
    return CostSummary(
        estimate_lo=estimate_lo,
        estimate_hi=estimate_hi,
        contingency=contingency,
        planning_total=total,
        travellers=travellers,
        largest_share=split(total, travellers)[0],
        status=status,
        ratio_pct=ratio,
        excess=excess,
        by_day=by_day,
        by_category=by_category,
        alerts=alerts,
        incomplete_items=incomplete,
        complete=bool(rows) and not incomplete,
    )
