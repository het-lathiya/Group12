"""Single-instance sliding windows for expensive requests (IMD-12, IMP-511)."""

import math
import time
from collections import deque
from collections.abc import Callable, Sequence

from fastapi import Request

from app.auth.deps import CurrentUser
from app.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.windows: dict[str, deque[float]] = {}
        self.next_cleanup = 0.0

    def check(self, keys: Sequence[str], limit: int) -> None:
        now = self.clock()
        cutoff = now - 60
        if now >= self.next_cleanup:
            self.windows = {
                key: values
                for key, values in self.windows.items()
                if values and values[-1] > cutoff
            }
            self.next_cleanup = now + 60
        windows = [self.windows.setdefault(key, deque()) for key in keys]
        for window in windows:
            while window and window[0] <= cutoff:
                window.popleft()
        retry = max(
            (max(1, math.ceil(window[0] + 60 - now)) for window in windows if len(window) >= limit),
            default=0,
        )
        if retry:
            raise RateLimited(retry_after_s=retry)
        for window in windows:
            window.append(now)


async def expensive_request(request: Request, user: CurrentUser) -> None:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = SlidingWindowLimiter()
        request.app.state.rate_limiter = limiter
    address = request.client.host if request.client else "unknown"
    limiter.check(
        [f"user:{user.user_id}", f"address:{address}"],
        request.app.state.settings.rate_limit_per_min,
    )
