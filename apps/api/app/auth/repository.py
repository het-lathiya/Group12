"""The profiles table (migration 0003). MOD-B02 is its only writer (§5.2, IMD-14)."""

from typing import Any
from uuid import UUID

from psycopg import errors as pg_errors
from sqlalchemy import func, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile as ProfileRow


async def insert_if_absent(session: AsyncSession, user_id: UUID) -> bool:
    """Insert the profile of ``user_id`` unless it exists (insert … on conflict do nothing).

    Returns False when no auth.users row has that id (the account no longer exists); the savepoint
    keeps the caller's transaction usable in that case.
    """
    statement = insert(ProfileRow).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
    try:
        async with session.begin_nested():
            await session.execute(statement)
    except IntegrityError as exc:
        if isinstance(exc.orig, pg_errors.ForeignKeyViolation):
            return False
        raise
    return True


async def mirror_auth_user(session: AsyncSession, user_id: UUID) -> None:
    """Insert the auth.users row of ``user_id`` on a stub database (A1 §5.1). The id only: the
    e-mail claim is never stored (NFR-020)."""
    await session.execute(
        text("insert into auth.users (id) values (:user_id) on conflict (id) do nothing"),
        {"user_id": user_id},
    )


async def get(session: AsyncSession, user_id: UUID) -> ProfileRow | None:
    return await session.get(ProfileRow, user_id, populate_existing=True)


async def update_profile(
    session: AsyncSession, user_id: UUID, values: dict[str, Any], *, acknowledge: bool
) -> None:
    """API-04: write the given columns of the caller's own row; ``acknowledge`` also sets
    ai_notice_ack_at to now (IMD-24). Nothing to write leaves the row as it is."""
    if acknowledge:
        values = {**values, "ai_notice_ack_at": func.now()}
    if values:
        await session.execute(update(ProfileRow).where(ProfileRow.id == user_id).values(**values))
