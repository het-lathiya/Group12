"""In-memory circuit breaker for generation calls (§8.4, FR-047; IMP-401, IMD-44).

One instance per provider, held by ``app.ai.factory``. It counts generations, not attempts: the
pipeline records each generation's provider result once, after the adapter's retries. It opens
after 5 consecutive transient failures (timeout, rate limit, unavailable) or at once on a quota or
auth error; cool-down 60 s after transient errors, 15 min after quota, and until restart after an
auth error. After the cool-down the next real request is the half-open probe: success closes it,
a failure opens it again. Embedding calls are never recorded here (Amendment A1, IMD-112).
"""

import time
from collections.abc import Callable
from typing import Final, Literal

from app.ai.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderFailureReason,
    ProviderQuotaExhausted,
)

State = Literal["closed", "open", "half_open"]

FAILURES_TO_OPEN: Final = 5
TRANSIENT_COOL_DOWN_S: Final = 60.0
QUOTA_COOL_DOWN_S: Final = 15 * 60.0


class CircuitBreaker:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._cool_down_s: float | None = None  # None while open: until restart (auth)
        self.open_reason: ProviderFailureReason | None = None

    @property
    def state(self) -> State:
        if self._opened_at is None:
            return "closed"
        if self._cool_down_s is not None and self._clock() - self._opened_at >= self._cool_down_s:
            return "half_open"
        return "open"

    def record_success(self) -> None:
        """The provider answered (an unusable answer included): close and reset the count."""
        self._failures = 0
        self._opened_at = None
        self.open_reason = None

    def record_failure(self, error: ProviderError) -> None:
        if isinstance(error, ProviderQuotaExhausted):
            self._open(error, QUOTA_COOL_DOWN_S)
        elif isinstance(error, ProviderAuthError):
            self._open(error, None)
        elif error.retryable:
            self._failures += 1
            if self.state == "half_open" or self._failures >= FAILURES_TO_OPEN:
                self._open(error, TRANSIENT_COOL_DOWN_S)
        # A bad request says nothing about the service's availability: neither counted nor reset.

    def _open(self, error: ProviderError, cool_down_s: float | None) -> None:
        self._opened_at = self._clock()
        self._cool_down_s = cool_down_s
        self.open_reason = error.failure_reason
