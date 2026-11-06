"""Profile service (MOD-B02): ensures, reads and updates the caller's profile (§3.4 rule 4, IMD-14;
the AI notice flag, IMD-24)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository
from app.auth.schemas import Profile, ProfilePatch
from app.core.errors import NotFound, Unauthenticated, ValidationFailed
from app.schemas.common import ErrorDetail


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
    """API-04, minimal form (IMP-305): only ai_notice_acknowledged true; IMP-601 adds the rest."""
    details = [
        ErrorDetail(field=name, message="This field cannot be changed yet.")
        for name in sorted(patch.model_fields_set - {"ai_notice_acknowledged"})
    ]
    if patch.ai_notice_acknowledged is not True:
        details.append(ErrorDetail(field="ai_notice_acknowledged", message="It must be true."))
    if details:
        raise ValidationFailed(details=details)
    await repository.set_ai_notice_ack(session, user_id)
    return await get_profile(session, user_id, email)


async def ai_notice_acknowledged(session: AsyncSession, user_id: UUID) -> bool:
    """Whether the caller has acknowledged the AI-provider notice (IMD-24, NFR-021)."""
    row = await repository.get(session, user_id)
    return row is not None and row.ai_notice_ack_at is not None
