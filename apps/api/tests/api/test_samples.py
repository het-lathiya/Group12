"""Saved sample itineraries, database side (§8.15, FR-036 AC3; IMP-402: TC-147 sample half, IMD-145).

Runs against the migrated test database with Sampleton loaded through the seed; every test is
rolled back. The reseed case deletes Sampleton's places and seeds again, as ``make db-reset &&
make seed`` would, so every place gets a new ID.
"""

import json
import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Destination, Place
from app.generation import samples
from app.places import seed

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"


async def load_sampleton(session: AsyncSession) -> Destination:
    await seed.load_fixture(session, seed.read_fixture(SAMPLETON))
    session.expire_all()
    destination = await session.scalar(select(Destination).where(Destination.slug == "sampleton"))
    assert destination is not None
    return destination


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    return await load_sampleton(db_session)


async def place_ids(session: AsyncSession, destination: Destination) -> dict[str, str]:
    rows = await session.execute(
        select(Place.external_ref, Place.id).where(Place.destination_id == destination.id)
    )
    return {str(ref): str(place_id) for ref, place_id in rows}


async def assert_loads_clean(session: AsyncSession, destination: Destination) -> None:
    ids = await place_ids(session, destination)
    names = samples.list_samples("sampleton")
    assert len(names) == 2
    for name in names:
        loaded = await samples.load_sample(session, "sampleton", name)
        stored = [i for d in loaded.sample.itinerary["days"] for i in d["items"]]
        planned = [i for d in loaded.plan for i in d.items]

        assert [f.code for f in loaded.findings if f.severity == "error"] == []
        # Each reference resolved to the current row, and step 9 gives back the stored times.
        assert [p.place_id for p in planned] == [
            ids[i["place_ref"]["external_ref"]] for i in stored
        ]
        assert [(p.start_time, p.duration_min) for p in planned] == [
            (i["start_time"], i["duration_min"]) for i in stored
        ]


@pytest.mark.asyncio
async def test_sample_both_samples_load_and_pass_validation(
    db_session: AsyncSession, sampleton: Destination
) -> None:
    await assert_loads_clean(db_session, sampleton)


@pytest.mark.asyncio
async def test_sample_samples_still_load_after_a_reseed(
    db_session: AsyncSession, sampleton: Destination
) -> None:
    before = await place_ids(db_session, sampleton)

    await db_session.execute(delete(Place).where(Place.destination_id == sampleton.id))
    reseeded = await load_sampleton(db_session)
    after = await place_ids(db_session, reseeded)

    assert after.keys() == before.keys()
    assert set(after.values()).isdisjoint(before.values())  # every place has a new ID
    await assert_loads_clean(db_session, reseeded)


@pytest.mark.asyncio
async def test_sample_unknown_external_ref_fails_loudly(
    db_session: AsyncSession,
    sampleton: Destination,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy = tmp_path / "sampleton" / samples.SAMPLE_DIR
    shutil.copytree(SAMPLETON / samples.SAMPLE_DIR, copy)
    path = copy / "two_day_walking.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["itinerary"]["days"][0]["items"][1]["place_ref"]["external_ref"] = "sample-999"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(samples, "SAMPLE_ROOTS", (tmp_path,))

    with pytest.raises(samples.UnresolvedPlaceRefError, match="sample-999") as error:
        await samples.load_sample(db_session, "sampleton", "two_day_walking")

    assert error.value.refs == [("SAMPLE fixture (synthetic)", "sample-999")]


@pytest.mark.asyncio
async def test_sample_inactive_place_is_not_resolved(
    db_session: AsyncSession, sampleton: Destination
) -> None:
    await db_session.execute(
        update(Place)
        .where(Place.destination_id == sampleton.id, Place.external_ref == "sample-006")
        .values(is_active=False)
    )

    with pytest.raises(samples.UnresolvedPlaceRefError, match="sample-006"):
        await samples.load_sample(db_session, "sampleton", "two_day_walking")
