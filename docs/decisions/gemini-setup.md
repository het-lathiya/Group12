# Gemini setup facts (IMP-301 step 1, OD-14)

- Date of every reading: 6 November 2026
- Status words: **Verified** means read on the official page in this run. **Unverified** means it could not be read or tested.
- Pages: every `ai.google.dev/gemini-api/docs/...` address now answers with a 301 to `aistudio.google.com/docs/...`, so the sources below are the redirect targets, which are Google's own pages.
- No key was used. No value in this file comes from a live call.

## Decisions taken from these facts

| Topic | Decision | Reason |
| --- | --- | --- |
| API style (OD-14) | Interactions API through `client.aio.interactions.create`, as a proposal for the team to confirm | It is the default of §8.4, it is Generally Available, and `store=false` is documented. The latency condition of §8.4 is still Unverified |
| Model | `GEMINI_MODEL_ID=gemini-3.5-flash-lite`, as a value for each environment | §8.4 asks for one specific stable ID. This candidate has the Stable badge; `gemini-3.8-flash` has the badge New |
| Thinking | `minimal` for `gemini-3.5-flash-lite` and `gemini-3.6-flash`, otherwise `low` | The lowest level each model accepts |
| Sampling | No `temperature`, `top_p` or `top_k` is sent | No page shows that the chosen model honours them |

`Settings.gemini_model_id` keeps its empty default: §4.5 sets it, and an empty value must stop start-up in staging and production (PD-IMP-301-1).

## Facts

| Fact | Status | Source |
| --- | --- | --- |
| `gemini-3.5-flash-lite` is listed with the Stable badge | Verified | https://aistudio.google.com/docs/models |
| `gemini-3.8-flash` is listed with the badge New, neither Stable nor Preview | Verified | https://aistudio.google.com/docs/models |
| `gemini-3.6-flash` and `gemini-3.1-flash-lite` are listed as Stable | Verified | https://aistudio.google.com/docs/models |
| `gemini-2.5-flash` is deprecated; from 1 December 2026 its requests route to `gemini-3.5-flash-lite` | Verified | https://aistudio.google.com/docs/models |
| Input and output token limits of the Flash and Flash-Lite models | Unverified (not on the page) | https://aistudio.google.com/docs/models |
| The Interactions API is Generally Available since June 2026, and `generateContent` stays fully supported | Verified | https://aistudio.google.com/docs/interactions-overview |
| Interactions are stored by default (`store=true`); `store=false` opts out and rules out background runs and `previous_interaction_id` | Verified | https://aistudio.google.com/docs/interactions-overview |
| An async Interactions example | Unverified (the page shows only a synchronous call) | https://aistudio.google.com/docs/interactions-overview |
| `client.aio.interactions.create` exists in `google-genai` 2.34.0 and works through a fake transport | Verified in the installed SDK, not on a page | SDK source |
| Latency of the async call against the target of §8.4 | Unverified (needs the key) | none |
| Structured output uses `response_format` with `type` `text`, `mime_type` `application/json` and `schema`; the answer is read from `output_text` | Verified | https://aistudio.google.com/docs/structured-output |
| `minLength` and `maxLength` are ignored by the server | Verified | https://aistudio.google.com/docs/structured-output |
| `$defs`, `$ref` and `anyOf` are supported; `format` is listed for strings | Verified | https://aistudio.google.com/docs/structured-output |
| `pattern` | Unverified (not on the page); the wire schema leaves it out | https://aistudio.google.com/docs/structured-output |
| Thinking is set by `generation_config={"thinking_level": ...}` | Verified | https://aistudio.google.com/docs/thinking |
| Levels: `gemini-3.5-flash-lite` and `gemini-3.6-flash` minimal to high; `gemini-3.8-flash` low to high | Verified | https://aistudio.google.com/docs/thinking |
| Whether `thinking_budget` and `thinking_level` may be sent together | Unverified (not on the page); only the level is sent | https://aistudio.google.com/docs/thinking |
| Thought tokens are in `usage.total_thought_tokens`, apart from output tokens (the page's example: 62 + 171 + 297 = 530 `total_tokens`) | Verified | https://aistudio.google.com/docs/thinking |
| `temperature` is a `generation_config` parameter | Verified | https://aistudio.google.com/docs/interactions-overview |
| The chosen model honours `temperature` | Unverified | none |
| Error body: `error.code` (snake_case) and `error.message`; codes include `rate_limit_exceeded`, `too_many_requests` and `quota_exceeded` (429), `payment_required` (402), `authentication` (401), `permission_denied` (403), `model_not_found` (404), `service_unavailable` (503), `deadline_exceeded` (504) | Verified | https://aistudio.google.com/docs/api-errors |
| Blocked codes: `safety`, `recitation`, `language`, `prohibited_content`, `spii`, `blocklist`, `content_blocked` | Verified | https://aistudio.google.com/docs/api-errors |
| The card's `jailbreak` code | Unverified (not on the page); kept in the blocked list | https://aistudio.google.com/docs/api-errors |
| Do not retry 400, 402 or 403; retry 408, 429 and 5xx with backoff | Verified | https://aistudio.google.com/docs/troubleshooting |
| Limits are measured as RPM, input TPM and RPD; tiers are Free and Tier 1 to 3; daily quotas reset at midnight Pacific time | Verified | https://aistudio.google.com/docs/rate-limits |
| Per-model limits for the Flash models | Unverified (the page sends the reader to AI Studio) | https://aistudio.google.com/docs/rate-limits |
| The team key's own rate limits | Unverified | none |
| Whether thinking is double counted in a live `usage` block | Unverified (needs the key) | none |

## SDK behaviour seen through a fake transport (`google-genai` 2.34.0)

These are observations of the installed package, not documented facts:

- `HttpRetryOptions(attempts=0)` and `attempts=1` still make one retry on 429 and 5xx, so the adapter lists a status no server sends as the only retryable one. `test_gemini_the_sdk_makes_one_attempt_only` guards this.
- The Interactions error classes are exported only from a private module, so the version is pinned exactly in `apps/api/pyproject.toml`.

## Live result

Live smoke (TC-029): pending — run by the key holder with make live-smoke; result recorded before SG-3

7 November 2026, key holder's local diagnostic (`gemini-3.5-flash-lite`, Interactions API): a plain call, `thinking_level` minimal and low, and a small `response_format` schema all succeed. The io-1 wire schema is refused with HTTP 400, code `invalid_request`, message "The specified schema produces a constraint that has too many states for serving". `make live-smoke`: 1 passed (embeddings), 1 failed (TC-029, HTTP 400). The wire schema now leaves out numeric, length, count and format limits (proposed D13, `docs/progress/parts/IMP-301-wire-schema.md`). TC-029 to be re-run by the key holder after this change.
