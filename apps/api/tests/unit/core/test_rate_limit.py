"""Sliding-window boundaries and UTC daily caps (IMP-511)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.errors import QuotaReached, RateLimited
from app.core.rate_limit import SlidingWindowLimiter
from app.generation import service


def test_rate_limit_tc_294_user_and_address_windows_and_exact_expiry() -> None:
    clock = [0.0]
    limiter = SlidingWindowLimiter(lambda: clock[0])
    limiter.check(["user:a", "address:a"], 1)
    for keys in (["user:a", "address:b"], ["user:b", "address:a"]):
        with pytest.raises(RateLimited) as error:
            limiter.check(keys, 1)
        assert error.value.retry_after_s == 60
    clock[0] = 59.1
    with pytest.raises(RateLimited) as error:
        limiter.check(["user:a", "address:a"], 1)
    assert error.value.retry_after_s == 1
    clock[0] = 60.0
    limiter.check(["user:a", "address:a"], 1)
    limiter.check(["user:b", "address:b"], 1)  # rejected requests consumed neither key


def test_rate_limit_prunes_expired_keys() -> None:
    clock = [0.0]
    limiter = SlidingWindowLimiter(lambda: clock[0])
    limiter.check(["expired"], 1)
    clock[0] = 61.0
    limiter.check(["new"], 1)
    assert "expired" not in limiter.windows


@pytest.mark.asyncio
@pytest.mark.parametrize(("counts", "scope"), [((10, 10), "user"), ((0, 200), "global")])
async def test_rate_limit_daily_quota_tc_171_tc_172_reset_at_next_utc_midnight(
    monkeypatch: pytest.MonkeyPatch, counts: tuple[int, int], scope: str
) -> None:
    now = datetime(2026, 11, 14, 23, 59, 59, tzinfo=UTC)

    async def usage(*args):
        assert args[2:] == service.utc_day(now)
        return counts

    monkeypatch.setattr(service.repository, "daily_usage", usage)
    monkeypatch.setenv("AI_DAILY_GENERATIONS_PER_USER", "10")
    monkeypatch.setenv("AI_DAILY_GENERATIONS_GLOBAL", "200")
    with pytest.raises(QuotaReached) as error:
        await service.check_daily_cap(object(), uuid4(), now)
    assert error.value.retry_after_s == 1
    assert {d.field: d.message for d in error.value.details} == {
        "scope": scope,
        "reset_at": "2026-11-15T00:00:00Z",
        "mode": "rule_based",
    }
