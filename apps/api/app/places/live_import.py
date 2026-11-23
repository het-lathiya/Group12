"""Import CLI for one live destination (Amendment A2 §6.2; IMP-725), for the staging window.

    python -m app.places.live_import --osm-ref R1234567
    python -m app.places.live_import --query "<city>"   # the first settlement the geocoder finds

It runs the same resolve-then-import path as API-77 and the job, synchronously: a destination that
is completed or has too little data and has not expired is only printed; a new one is created and
a failed, expired or queued one is queued again, then the import runs inline (not through
``submit``). It is idempotent per OSM reference. The CLI has no user, so ``import_requested_by``
stays null and the per-user daily cap does not apply. The providers come from
``LIVE_DATA_PROVIDER``; the factory refuses FAKE outside local and test.

Exit codes: 0 completed or not enough data; 1 the import failed or the city cannot be imported;
2 bad arguments; 3 another process is running the import.
"""

import argparse
import asyncio
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Destination as DestinationRow
from app.db.session import get_engine, transaction
from app.livedata.countries import choose_timezone, clip_bbox, country
from app.livedata.factory import LiveProviders, get_providers
from app.livedata.providers.base import SETTLEMENT_KINDS, GeoPlace, LiveDataError
from app.places import live_jobs, repository
from app.places.live_service import (
    COUNTRY_NOT_SUPPORTED,
    NAME_MAX_CHARS,
    NOT_A_SETTLEMENT,
    PROVIDER,
    live_slug,
)

EXIT_OK: Final = 0
EXIT_FAILED: Final = 1
EXIT_USAGE: Final = 2
EXIT_BUSY: Final = 3
OSM_REF_PATTERN: Final = r"^[NWR][0-9]{1,12}$"
_SIX_PLACES: Final = Decimal("0.000001")


class CannotImportError(Exception):
    """The reference or query gives no importable settlement; the message is printed."""


@dataclass(frozen=True)
class Outcome:
    destination_id: UUID
    ran: bool  # False: the existing state was only printed
    row: DestinationRow


def _six(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)


def build_live_row(place: GeoPlace, osm_ref: str) -> DestinationRow:
    """The queued, inactive live destination of one settlement, with no requesting user.

    The same rules as API-77 (A2 §6.1): slug, English name, clipped box, the country's currency
    and the nearest zone.
    """
    if place.kind not in SETTLEMENT_KINDS:
        raise CannotImportError(NOT_A_SETTLEMENT)
    facts = country(place.country_code)
    timezone = choose_timezone(place.country_code, place.lat, place.lon)
    if facts is None or timezone is None:
        raise CannotImportError(COUNTRY_NOT_SUPPORTED)
    name = (place.name_en or place.name).strip()[:NAME_MAX_CHARS]
    box = clip_bbox(place.lat, place.lon, place.bbox)
    return DestinationRow(
        slug=live_slug(name, osm_ref),
        name=name,
        region=place.region,
        country_code=facts.code,
        timezone=timezone,
        currency=facts.currency,
        center_lat=_six(place.lat),
        center_lon=_six(place.lon),
        bbox_min_lat=_six(box.south),
        bbox_max_lat=_six(box.north),
        bbox_min_lon=_six(box.west),
        bbox_max_lon=_six(box.east),
        is_active=False,
        is_sample=False,
        data_tier="live",
        provider=PROVIDER,
        external_ref=osm_ref,
        import_status="queued",
        import_requested_by=None,
    )


async def _osm_ref_for_query(providers: LiveProviders, query: str) -> str:
    try:
        found = await providers.geocoder.search(query)
    except LiveDataError as exc:
        raise CannotImportError(f"The geocoder is not available ({exc}).") from None
    for candidate in found:
        if candidate.kind in SETTLEMENT_KINDS:
            return candidate.osm_ref
    raise CannotImportError("No city, town or village matches the query.")


def _current(row: DestinationRow, now: datetime) -> bool:
    """Completed or not enough data, and not expired: nothing to do."""
    fresh = row.expires_at is None or row.expires_at > now
    return row.import_status in ("completed", "insufficient_data") and fresh


async def _prepare(session: AsyncSession, providers: LiveProviders, osm_ref: str) -> Outcome:
    """The existing row as it is, or a new or re-queued row ready for the import."""
    now = datetime.now(UTC)
    existing = await repository.destination_by_ref(session, PROVIDER, osm_ref)
    if existing is not None:
        if _current(existing, now) or existing.import_status == "running":
            return Outcome(existing.id, ran=False, row=existing)
        if existing.import_status != "queued":
            await repository.requeue_live_import(session, existing.id)
        return Outcome(existing.id, ran=True, row=existing)
    try:
        place = await providers.geocoder.lookup(osm_ref)
    except LiveDataError as exc:
        raise CannotImportError(f"The geocoder is not available ({exc}).") from None
    if place is None:
        raise CannotImportError("No settlement has this OSM reference.")
    row = build_live_row(place, osm_ref)
    try:
        async with session.begin_nested():
            row = await repository.insert_live_destination(session, row)
    except IntegrityError:
        raced = await repository.destination_by_ref(session, PROVIDER, osm_ref)
        if raced is None:
            raise
        return Outcome(raced.id, ran=False, row=raced)
    return Outcome(row.id, ran=True, row=row)


async def import_destination(
    *,
    osm_ref: str | None = None,
    query: str | None = None,
    providers: LiveProviders | None = None,
    sessions: live_jobs.Sessions = transaction,
) -> Outcome:
    """Resolve the settlement and run its import inline when needed; the final row is returned."""
    providers = providers or get_providers()
    if osm_ref is None:
        if query is None:
            raise CannotImportError("Give --osm-ref or --query.")
        osm_ref = await _osm_ref_for_query(providers, query)
    async with sessions() as session:
        prepared = await _prepare(session, providers, osm_ref)
    if not prepared.ran:
        return prepared
    await live_jobs.run_import(prepared.destination_id, providers=providers, sessions=sessions)
    async with sessions() as session:
        row = await repository.destination_by_id(session, prepared.destination_id)
        if row is None:  # never deleted; only a concurrent reset of the database could do it
            raise CannotImportError("The destination disappeared during the import.")
        await session.refresh(row)
    return Outcome(prepared.destination_id, ran=True, row=row)


def _lines(outcome: Outcome) -> list[str]:
    row = outcome.row
    return [
        f"destination_id: {row.id}",
        f"slug: {row.slug}",
        f"import_ran: {'yes' if outcome.ran else 'no (existing state)'}",
        f"import_status: {row.import_status}",
        f"failure_reason: {row.import_failure_reason or '-'}",
        f"places_found: {row.places_found if row.places_found is not None else '-'}",
        f"places_usable: {row.places_usable if row.places_usable is not None else '-'}",
        f"nearby_city: {row.nearby_city or '-'}",
        f"is_active: {row.is_active}",
        f"imported_at: {row.imported_at.isoformat() if row.imported_at else '-'}",
        f"expires_at: {row.expires_at.isoformat() if row.expires_at else '-'}",
    ]


def exit_code(outcome: Outcome) -> int:
    status = outcome.row.import_status
    if status in ("completed", "insufficient_data"):
        return EXIT_OK
    if status in ("running", "queued"):
        return EXIT_BUSY
    return EXIT_FAILED


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.places.live_import",
        description="Import one live destination from OpenStreetMap (Amendment A2 §6.2).",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--osm-ref", help="Nominatim OSM reference, for example R1234567")
    target.add_argument("--query", help="City name; the first settlement found is imported")
    args = parser.parse_args(argv)
    if args.osm_ref is not None and not re.fullmatch(OSM_REF_PATTERN, args.osm_ref):
        parser.error("--osm-ref must look like R1234567 (N, W or R and 1 to 12 digits)")
    return args


async def _main(args: argparse.Namespace) -> int:
    get_settings()  # refuses an invalid configuration before any work
    try:
        outcome = await import_destination(osm_ref=args.osm_ref, query=args.query)
    except CannotImportError as exc:
        print(f"cannot import: {exc}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        await get_engine().dispose()
    for line in _lines(outcome):
        print(line)
    return exit_code(outcome)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
