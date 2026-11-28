# Groq chat-completion format fixtures (IMD-223, IMP-512)

These are synthetic recordings of the documented HTTP shape, not captures from a live account.
They contain SAMPLE place IDs and no key, request prompt or personal data. The contract suite
replays them through `httpx.MockTransport`; timeouts use a transport exception.

| File | Contract |
| --- | --- |
| `ok.json` | io-1 candidate, actual model and reported token usage |
| `malformed.json` | `ProviderInvalidOutput(malformed_json)` |
| `rate_limited_429.json` | `ProviderRateLimited`, `retry-after` respected |
| `unavailable_503.json` | `ProviderUnavailable` |
| `quota_402.json` | `ProviderQuotaExhausted` (all Groq 429 responses remain rate limits) |
| `permission_denied_403.json` | `ProviderAuthError` |
| `model_not_found_404.json` | `ProviderBadRequest` |

Wire documentation: [chat completions](https://console.groq.com/docs/api-reference),
[structured outputs](https://console.groq.com/docs/structured-outputs),
[rate-limit headers](https://console.groq.com/docs/rate-limits); read 2026-11-28.
