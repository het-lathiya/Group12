"""Profile service (MOD-B02): ensures, reads and updates the caller's profile (§3.4 rule 4, IMD-14;
the AI notice flag, IMD-24; the editable fields of FR-004, IMP-601)."""

import re
from typing import Any, Final
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository
from app.auth.schemas import Profile, ProfilePatch
from app.core.errors import NotFound, Unauthenticated, ValidationFailed
from app.schemas.common import ErrorDetail
from app.trips.schemas import PreferencesIn

CURRENCY: Final = re.compile(r"^[A-Z]{3}$")  # ISO 4217, as profiles.preferred_currency
COUNTRY: Final = re.compile(r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2, as profiles.home_country
NOT_DEFAULTS: Final = ("notes", "must_visit_place_ids")  # IMD-16: trip-only PreferencesIn keys


async def get_or_create_profile(
    session: AsyncSession, user_id: UUID, *, mirror_auth_user: bool = False
) -> None:
    """Create the profile row on the first authenticated call; later calls change nothing.

    Called only by the CurrentUser dependency; trips.user_id references profiles.id, so the row
    must exist before any trip is written. With ``mirror_auth_user`` (DB_AUTH_STUB, A1 §5.1) the
    user's auth.users row is created first, in the same transaction, for a database whose auth
    schema is the stub and whose users live in hosted Supabase Auth.
    """
    if mirror_auth_user:
        await repository.mirror_auth_user(session, user_id)
    if not await repository.insert_if_absent(session, user_id):
        # A valid token for an account that no longer exists in auth.users.
        raise Unauthenticated()


async def get_profile(session: AsyncSession, user_id: UUID, email: str | None) -> Profile:
    row = await repository.get(session, user_id)
    if row is None:
        raise NotFound()
    return Profile(
        id=row.id,
        email=email,
        display_name=row.display_name,
        home_country=row.home_country,
        preferred_currency=row.preferred_currency,
        default_preferences=row.default_preferences,
        ai_notice_ack_at=row.ai_notice_ack_at,
    )


async def update_profile(
    session: AsyncSession, user_id: UUID, email: str | None, patch: ProfilePatch
) -> Profile:
    """API-04: change the fields sent (FR-004); null clears a text field. Every rule is checked
    before anything is written, so a 422 changes nothing."""
    sent = patch.model_fields_set
    details: list[ErrorDetail] = []
    values: dict[str, Any] = {}
    if "ai_notice_acknowledged" in sent and patch.ai_notice_acknowledged is not True:
        details.append(ErrorDetail(field="ai_notice_acknowledged", message="It must be true."))
    if "display_name" in sent:
        values["display_name"] = patch.display_name  # 1 to 60 is checked by ProfilePatch
    for name, pattern, message in (
        ("preferred_currency", CURRENCY, "Enter a three-letter ISO 4217 code, such as INR."),
        ("home_country", COUNTRY, "Enter a two-letter ISO 3166-1 country code, such as IN."),
    ):
        if name in sent:
            value = getattr(patch, name)
            if value is not None and not pattern.fullmatch(value):
                details.append(ErrorDetail(field=name, message=message))
            values[name] = value
    if "default_preferences" in sent:
        defaults, errors = _default_preferences(patch.default_preferences or {})
        details.extend(errors)
        values["default_preferences"] = defaults
    if details:
        raise ValidationFailed(details=details)
    await repository.update_profile(
        session, user_id, values, acknowledge=patch.ai_notice_acknowledged is True
    )
    return await get_profile(session, user_id, email)


def _default_preferences(raw: dict[str, Any]) -> tuple[dict[str, Any], list[ErrorDetail]]:
    """IMD-16: the PreferencesIn rules without notes and must-visit places; omitted keys take the
    PreferencesIn defaults, so a new trip can be prefilled from the stored object as it is."""
    field = "default_preferences"
    errors = [
        ErrorDetail(field=f"{field}.{key}", message="This preference belongs to a trip only.")
        for key in NOT_DEFAULTS
        if key in raw
    ]
    try:
        parsed = PreferencesIn.model_validate(
            {k: v for k, v in raw.items() if k not in NOT_DEFAULTS}
        )
    except ValidationError as exc:
        errors.extend(
            ErrorDetail(
                field=".".join([field, *(str(part) for part in error["loc"])]),
                message=error["msg"],
            )
            for error in exc.errors()
        )
        return {}, errors
    return parsed.model_dump(mode="json", exclude=set(NOT_DEFAULTS)), errors


async def ai_notice_acknowledged(session: AsyncSession, user_id: UUID) -> bool:
    """Whether the caller has acknowledged the AI-provider notice (IMD-24, NFR-021)."""
    row = await repository.get(session, user_id)
    return row is not None and row.ai_notice_ack_at is not None
