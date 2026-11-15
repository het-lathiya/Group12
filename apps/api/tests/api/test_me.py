"""API-03 GET /api/v1/me and first-call profile creation (§6.6.1, IMD-14; IMP-108: TC-057).
API-04 PATCH /api/v1/me: the AI notice flag (IMD-24; IMP-305) and the editable profile fields
(FR-004, IMD-16; IMP-601: TC-060 to TC-062).

Runs against the migrated test database (tests/fixtures/db.py); every test is rolled back.
"""

import uuid
from typing import Any

import httpx
import pytest
from fixtures.auth import AuthUser, bearer, make_token
from fixtures.db import insert_auth_user
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile as ProfileRow

PROFILE_FIELDS = {
    "id",
    "email",
    "display_name",
    "home_country",
    "preferred_currency",
    "default_preferences",
    "ai_notice_ack_at",
}


async def profile_rows(session: AsyncSession, user_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(ProfileRow).where(ProfileRow.id == user_id)
    return int((await session.execute(query)).scalar_one())


@pytest.mark.asyncio
async def test_me_creates_exactly_one_profile_on_the_first_call(
    api_client: httpx.AsyncClient, db_session: AsyncSession, auth_user: AuthUser
) -> None:
    assert await profile_rows(db_session, auth_user.user_id) == 0

    first = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert first.status_code == 200
    assert await profile_rows(db_session, auth_user.user_id) == 1

    second = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert await profile_rows(db_session, auth_user.user_id) == 1


@pytest.mark.asyncio
async def test_tc_057_me_returns_the_token_users_profile(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.get("/api/v1/me", headers=auth_user.headers)

    assert response.status_code == 200
    profile = response.json()
    assert set(profile) == PROFILE_FIELDS
    assert profile["id"] == str(auth_user.user_id)
    # The email comes from the token; it is not stored in profiles.
    assert profile["email"] == auth_user.email
    assert profile["display_name"] is None
    assert profile["default_preferences"] == {}
    assert profile["ai_notice_ack_at"] is None


@pytest.mark.asyncio
async def test_me_never_returns_another_users_profile(
    api_client: httpx.AsyncClient, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    other = uuid.uuid4()
    await insert_auth_user(db_session, other)
    mine = (await api_client.get("/api/v1/me", headers=auth_user.headers)).json()
    theirs = (await api_client.get("/api/v1/me", headers=bearer(make_token(other)))).json()

    assert mine["id"] == str(auth_user.user_id)
    assert theirs["id"] == str(other)


@pytest.mark.asyncio
async def test_me_without_a_token_is_401_and_creates_nothing(
    api_client: httpx.AsyncClient, db_session: AsyncSession, auth_user: AuthUser
) -> None:
    response = await api_client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert await profile_rows(db_session, auth_user.user_id) == 0


@pytest.mark.asyncio
async def test_a_valid_token_for_a_deleted_account_is_401(
    api_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    # Signed correctly, but no auth.users row exists: no profile can be created for it.
    ghost = uuid.uuid4()
    response = await api_client.get("/api/v1/me", headers=bearer(make_token(ghost)))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert await profile_rows(db_session, ghost) == 0


# API-04: the AI notice flag (IMD-24)


@pytest.mark.asyncio
async def test_ai_notice_acknowledged_true_sets_the_timestamp(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    before = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert before.json()["ai_notice_ack_at"] is None

    response = await api_client.patch(
        "/api/v1/me", json={"ai_notice_acknowledged": True}, headers=auth_user.headers
    )

    assert response.status_code == 200, response.text
    profile = response.json()
    assert set(profile) == PROFILE_FIELDS
    assert profile["id"] == str(auth_user.user_id)
    assert profile["email"] == auth_user.email
    assert profile["ai_notice_ack_at"] is not None
    after = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert after.json() == profile


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({"ai_notice_acknowledged": False}, ["ai_notice_acknowledged"]),
        ({"ai_notice_acknowledged": None}, ["ai_notice_acknowledged"]),
        (
            {"ai_notice_acknowledged": True, "preferred_currency": "inr"},
            ["preferred_currency"],
        ),
    ],
    ids=["false", "null", "with_an_invalid_field"],
)
async def test_ai_notice_patch_accepts_only_the_true_flag(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    body: dict[str, Any],
    fields: list[str],
) -> None:
    response = await api_client.patch("/api/v1/me", json=body, headers=auth_user.headers)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in response.json()["error"]["details"]] == fields
    profile = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert profile.json()["ai_notice_ack_at"] is None


@pytest.mark.asyncio
async def test_ai_notice_patch_refuses_an_unknown_field(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.patch(
        "/api/v1/me",
        json={"ai_notice_acknowledged": True, "user_id": str(uuid.uuid4())},
        headers=auth_user.headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_ai_notice_patch_changes_only_the_callers_profile(
    api_client: httpx.AsyncClient, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    other = uuid.uuid4()
    await insert_auth_user(db_session, other)
    other_headers = bearer(make_token(other))
    await api_client.get("/api/v1/me", headers=other_headers)

    await api_client.patch(
        "/api/v1/me", json={"ai_notice_acknowledged": True}, headers=auth_user.headers
    )

    theirs = await api_client.get("/api/v1/me", headers=other_headers)
    assert theirs.json()["ai_notice_ack_at"] is None


@pytest.mark.asyncio
async def test_ai_notice_patch_without_a_token_is_401(api_client: httpx.AsyncClient) -> None:
    response = await api_client.patch("/api/v1/me", json={"ai_notice_acknowledged": True})

    assert response.status_code == 401


# API-04: the editable profile fields (FR-004, IMD-16; IMP-601)

DEFAULTS = {
    "interests": ["museum", "food"],
    "pace": "relaxed",
    "budget_priority": "saving",
    "transport_pref": "local_transport",
    "accommodation_type": "any",
    "step_free_required": True,
}


# FR-004 AC1, TC-060


@pytest.mark.asyncio
async def test_tc_060_a_display_name_of_1_to_60_characters_is_saved_and_shown(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    for name in ("A", "  Asha Patel  ", "x" * 60):
        response = await api_client.patch(
            "/api/v1/me", json={"display_name": name}, headers=auth_user.headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["display_name"] == name.strip()
        shown = await api_client.get("/api/v1/me", headers=auth_user.headers)
        assert shown.json()["display_name"] == name.strip()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
async def test_tc_060_a_display_name_outside_1_to_60_is_rejected(
    api_client: httpx.AsyncClient, auth_user: AuthUser, name: str
) -> None:
    response = await api_client.patch(
        "/api/v1/me", json={"display_name": name}, headers=auth_user.headers
    )

    assert response.status_code == 422, response.text
    assert [d["field"] for d in response.json()["error"]["details"]] == ["display_name"]
    profile = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert profile.json()["display_name"] is None


# FR-004 AC2, TC-061


@pytest.mark.asyncio
async def test_tc_061_default_preferences_currency_and_country_are_saved(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.patch(
        "/api/v1/me",
        json={
            "preferred_currency": "INR",
            "home_country": "IN",
            "default_preferences": DEFAULTS,
        },
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["preferred_currency"] == "INR"
    assert profile["home_country"] == "IN"
    assert profile["default_preferences"] == DEFAULTS
    assert profile["ai_notice_ack_at"] is None  # untouched by other fields
    assert (await api_client.get("/api/v1/me", headers=auth_user.headers)).json() == profile


@pytest.mark.asyncio
async def test_omitted_default_preferences_take_the_trip_defaults(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.patch(
        "/api/v1/me",
        json={"default_preferences": {"pace": "busy"}},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["default_preferences"] == {
        "interests": [],
        "pace": "busy",
        "budget_priority": "balanced",
        "transport_pref": "walking",
        "accommodation_type": "any",
        "step_free_required": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("defaults", "fields"),
    [
        ({"pace": "sprint"}, ["default_preferences.pace"]),
        ({"interests": ["stay"]}, ["default_preferences.interests.0"]),
        ({"notes": "Trip only."}, ["default_preferences.notes"]),
        ({"must_visit_place_ids": []}, ["default_preferences.must_visit_place_ids"]),
        ({"colour": "blue"}, ["default_preferences.colour"]),
    ],
    ids=["bad_pace", "stay_interest", "notes", "must_visit", "unknown_key"],
)
async def test_default_preferences_follow_the_preferences_rules(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    defaults: dict[str, Any],
    fields: list[str],
) -> None:
    response = await api_client.patch(
        "/api/v1/me",
        json={"display_name": "Asha", "default_preferences": defaults},
        headers=auth_user.headers,
    )

    assert response.status_code == 422, response.text
    assert [d["field"] for d in response.json()["error"]["details"]] == fields
    profile = (await api_client.get("/api/v1/me", headers=auth_user.headers)).json()
    assert profile["display_name"] is None  # nothing is written on a 422
    assert profile["default_preferences"] == {}


# FR-004 AC3, TC-062


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["inr", "IN", "RUPEE", "12A", ""])
async def test_tc_062_an_invalid_currency_code_is_rejected(
    api_client: httpx.AsyncClient, auth_user: AuthUser, currency: str
) -> None:
    response = await api_client.patch(
        "/api/v1/me", json={"preferred_currency": currency}, headers=auth_user.headers
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [d["field"] for d in error["details"]] == ["preferred_currency"]
    profile = await api_client.get("/api/v1/me", headers=auth_user.headers)
    assert profile.json()["preferred_currency"] is None


@pytest.mark.asyncio
async def test_an_invalid_home_country_is_rejected(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    response = await api_client.patch(
        "/api/v1/me", json={"home_country": "IND"}, headers=auth_user.headers
    )

    assert response.status_code == 422, response.text
    assert [d["field"] for d in response.json()["error"]["details"]] == ["home_country"]


@pytest.mark.asyncio
async def test_null_clears_a_profile_field(
    api_client: httpx.AsyncClient, auth_user: AuthUser
) -> None:
    await api_client.patch(
        "/api/v1/me",
        json={"display_name": "Asha", "preferred_currency": "INR"},
        headers=auth_user.headers,
    )

    response = await api_client.patch(
        "/api/v1/me", json={"display_name": None}, headers=auth_user.headers
    )

    assert response.json()["display_name"] is None
    assert response.json()["preferred_currency"] == "INR"


@pytest.mark.asyncio
async def test_the_profile_id_is_the_token_user_and_a_body_user_id_is_rejected(
    api_client: httpx.AsyncClient, auth_user: AuthUser, db_session: AsyncSession
) -> None:
    other = uuid.uuid4()
    await insert_auth_user(db_session, other)

    refused = await api_client.patch(
        "/api/v1/me",
        json={"display_name": "Asha", "user_id": str(other)},
        headers=auth_user.headers,
    )
    saved = await api_client.patch(
        "/api/v1/me", json={"display_name": "Asha"}, headers=auth_user.headers
    )

    assert refused.status_code == 422
    assert [d["field"] for d in refused.json()["error"]["details"]] == ["user_id"]
    assert saved.json()["id"] == str(auth_user.user_id)
    assert await profile_rows(db_session, other) == 0
