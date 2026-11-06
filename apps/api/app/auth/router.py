"""API-03 GET /api/v1/me (specification §6.6.1; FR-002, FR-003, FR-004; IMD-14).

API-04 PATCH /api/v1/me accepts only ai_notice_acknowledged: true (IMP-305, IMD-24); IMP-601 adds
the editable profile fields of its declared shape.
"""

from fastapi import APIRouter

from app.auth import service
from app.auth.deps import CurrentUser, DbSession
from app.auth.schemas import Profile, ProfilePatch

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=Profile, summary="API-03 Read my profile")
async def get_me(user: CurrentUser, session: DbSession) -> Profile:
    # The profile row was ensured by CurrentUser in this same request (IMD-14).
    return await service.get_profile(session, user.user_id, user.email)


@router.patch("/me", response_model=Profile, summary="API-04 Update my profile")
async def update_me(body: ProfilePatch, user: CurrentUser, session: DbSession) -> Profile:
    return await service.update_profile(session, user.user_id, user.email, body)
