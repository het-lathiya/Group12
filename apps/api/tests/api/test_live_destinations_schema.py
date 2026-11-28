"""Migration 0008 live destination columns (IMP-721; TC-463; Amendment A2 §4.1).

Runs against the migrated test database; each test rolls back. The rows are SAMPLE destinations
written straight through the ORM, so the CHECKs and the unique index of 0008 are what accept or
reject them. The Sampleton fixture stands for the existing curated rows.
"""

import uuid
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from fixtures.db import insert_auth_user
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import health
from app.db.models import Destination, Profile
from app.places import seed

SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"


def _destination(**overrides: object) -> Destination:
    """A SAMPLE live destination that satisfies every 0008 constraint unless overridden."""
    suffix = uuid.uuid4().hex[:8]
    values: dict[str, object] = {
        "slug": f"live-liveton-sample-{suffix}",
        "name": "Liveton (SAMPLE)",
        "country_code": "IN",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "center_lat": Decimal("23.000000"),
        "center_lon": Decimal("72.000000"),
        "bbox_min_lat": Decimal("22.900000"),
        "bbox_max_lat": Decimal("23.100000"),
        "bbox_min_lon": Decimal("71.900000"),
        "bbox_max_lon": Decimal("72.100000"),
        "is_active": False,
        "is_sample": False,
        "data_tier": "live",
        "provider": "osm",
        "external_ref": f"R{uuid.uuid4().int % 10**9}",
        "import_status": "queued",
    }
    values.update(overrides)
    return Destination(**values)


async def _rejected(session: AsyncSession, sqlstate: str, *rows: Destination) -> None:
    savepoint = await session.begin_nested()
    session.add_all(rows)
    with pytest.raises(IntegrityError) as raised:
        await session.flush()
    await savepoint.rollback()
    assert getattr(raised.value.orig, "sqlstate", None) == sqlstate


@pytest.mark.asyncio
async def test_live_destinations_schema_accepts_a_valid_live_row(db_session: AsyncSession) -> None:
    row = _destination()
    db_session.add(row)
    await db_session.flush()
    await db_session.refresh(row)
    assert row.data_tier == "live"
    assert row.import_status == "queued"


@pytest.mark.asyncio
async def test_live_destinations_schema_existing_rows_read_curated(
    db_session: AsyncSession,
) -> None:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    sampleton = await db_session.scalar(select(Destination).where(Destination.slug == "sampleton"))
    assert sampleton is not None
    assert sampleton.data_tier == "curated"
    assert sampleton.provider is None
    assert sampleton.external_ref is None
    assert sampleton.import_status is None
    other_tiers = await db_session.scalar(
        text("select count(*) from public.destinations where data_tier <> 'curated'")
    )
    assert other_tiers == 0


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_live_row_without_external_ref(
    db_session: AsyncSession,
) -> None:
    await _rejected(db_session, CHECK_VIOLATION, _destination(external_ref=None))


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_curated_row_with_import_status(
    db_session: AsyncSession,
) -> None:
    row = _destination(data_tier="curated", provider=None, external_ref=None)
    await _rejected(db_session, CHECK_VIOLATION, row)


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_live_sample_row(db_session: AsyncSession) -> None:
    await _rejected(db_session, CHECK_VIOLATION, _destination(is_sample=True))


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_failed_row_without_reason(
    db_session: AsyncSession,
) -> None:
    await _rejected(db_session, CHECK_VIOLATION, _destination(import_status="failed"))


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_reason_without_failure(
    db_session: AsyncSession,
) -> None:
    row = _destination(import_status="completed", import_failure_reason="timeout")
    await _rejected(db_session, CHECK_VIOLATION, row)


@pytest.mark.asyncio
async def test_live_destinations_schema_accepts_failed_row_with_reason(
    db_session: AsyncSession,
) -> None:
    db_session.add(_destination(import_status="failed", import_failure_reason="rate_limited"))
    await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"data_tier": "remote"},
        {"provider": "google"},
        {"external_ref": "X123"},
        {"external_ref": "R1234567890123"},
        {"import_status": "done"},
        {"import_status": "failed", "import_failure_reason": "unknown"},
        {"places_found": -1},
        {"places_usable": -1},
        {"nearby_city": ""},
        {"nearby_city": "Bigtown (SAMPLE)"},
    ],
    ids=[
        "tier",
        "provider",
        "ref-format",
        "ref-length",
        "status",
        "reason",
        "found",
        "usable",
        "nearby-empty",
        "nearby-without-insufficient-data",
    ],
)
async def test_live_destinations_schema_rejects_out_of_range_values(
    db_session: AsyncSession, overrides: dict[str, object]
) -> None:
    await _rejected(db_session, CHECK_VIOLATION, _destination(**overrides))


@pytest.mark.asyncio
async def test_live_destinations_schema_accepts_insufficient_data_with_nearby_city(
    db_session: AsyncSession,
) -> None:
    row = _destination(
        import_status="insufficient_data",
        places_found=12,
        places_usable=9,
        nearby_city="Bigtown (SAMPLE)",
    )
    db_session.add(row)
    await db_session.flush()


@pytest.mark.asyncio
async def test_live_destinations_schema_rejects_duplicate_provider_ref(
    db_session: AsyncSession,
) -> None:
    db_session.add(_destination(external_ref="R1234567"))
    await db_session.flush()
    await _rejected(db_session, UNIQUE_VIOLATION, _destination(external_ref="R1234567"))


@pytest.mark.asyncio
async def test_live_destinations_schema_requester_is_set_null_on_profile_delete(
    db_session: AsyncSession,
) -> None:
    user_id = await insert_auth_user(db_session)
    db_session.add(Profile(id=user_id, display_name="Sample traveller"))
    await db_session.flush()
    row = _destination(import_requested_by=user_id)
    db_session.add(row)
    await db_session.flush()
    await db_session.execute(text("delete from public.profiles where id = :id"), {"id": user_id})
    await db_session.refresh(row)
    assert row.import_requested_by is None


@pytest.mark.asyncio
async def test_live_destinations_schema_indexes_exist(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text(
            "select indexname, indexdef from pg_indexes "
            "where schemaname = 'public' and tablename = 'destinations'"
        )
    )
    indexes: dict[str, str] = dict(rows.all())
    assert "UNIQUE" in indexes["ux_destinations_provider_ref"]
    assert "WHERE (external_ref IS NOT NULL)" in indexes["ux_destinations_provider_ref"]
    assert "import_status" in indexes["ix_destinations_import_active"]
    assert "import_requested_by" in indexes["ix_destinations_import_requester"]


def test_live_destinations_schema_migration_0008_present_and_chain_linear() -> None:
    files = sorted(path.name for path in MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.py"))
    scripts = ScriptDirectory(str(MIGRATIONS.parent))
    assert len(scripts.get_heads()) == 1
    revisions = list(reversed(list(scripts.walk_revisions())))
    assert {Path(revision.path).name for revision in revisions} == set(files)
    assert revisions[0].down_revision is None
    for previous, current in pairwise(revisions):
        assert current.down_revision == previous.revision

    migration_0008 = scripts.get_revision("0008")
    assert migration_0008 is not None
    assert Path(migration_0008.path).name == "0008_live_destinations.py"
    migration_0009 = scripts.get_revision("0009")
    assert migration_0009 is not None
    assert migration_0009.down_revision == "0008"

    assert Path(revisions[-1].path).name == files[-1]
    assert revisions[-1].revision == scripts.get_current_head()
    assert scripts.get_current_head() == health.MIGRATION_HEAD
