# Gemini format fixtures

These files are format fixtures, not live recordings. They were written by hand to the documented Interactions response and API error formats (see `docs/decisions/gemini-setup.md`), because the key was not available when they were made. Replace them with sanitised recordings once a live run exists (`make live-smoke`).

Each file is `{"http_status", "headers", "body"}` and is replayed through a fake HTTP transport, so the real SDK parses it and nothing reaches the network. They hold no key and no personal data, and every place ID belongs to the SAMPLE test request.

| File | Case |
| --- | --- |
| `ok.json` | A completed interaction with a valid io-1 answer |
| `empty.json` | Completed, with empty text |
| `truncated.json` | Status `incomplete`, cut-off text |
| `malformed.json` | Completed, with text that is not JSON |
| `schema_violation.json` | Completed, with JSON that is not io-1 |
| `blocked.json` | HTTP 400 with the code `safety` |
| `blocked_status.json` | Status `failed` with the code `prohibited_content` |
| `rate_limited_429.json` | HTTP 429 `rate_limit_exceeded` with `Retry-After` |
| `quota_429.json` | HTTP 429 `quota_exceeded` |
| `unavailable_503.json` | HTTP 503 `service_unavailable` |
| `permission_denied_403.json` | HTTP 403 `permission_denied` (the provider contract suite's auth case, IMP-512) |
| `model_not_found_404.json` | HTTP 404 `model_not_found` (the provider contract suite's bad-request case, IMP-512) |
