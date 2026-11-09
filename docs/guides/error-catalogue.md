# Error catalogue

FR-116, IMP-412. The web app shows every failed request through `ErrorState`, using this catalogue. The same text is in `apps/web/lib/api/errors.ts` (`ERROR_CATALOGUE`). Change both together.

There is one entry per error code of specification §6.3, plus "network error" for requests that never reached the API. A new code needs a §6.3 change first, so do not add a code here on your own.

## How a failed request is shown

`ErrorState` reads the error through `describeError` and shows:

1. **What happened.** This is the page's own title when it gives one (for example "Your trips could not be loaded"), otherwise the catalogue's "what happened".
2. **The API's message.** §6.3 says `message` is safe to show. Plain text only: a JSON body, a multi-line dump or a stack trace is never shown.
3. **What to do next.** This comes from the catalogue. For `RATE_LIMITED` with `retry_after_s`, the line "Try again in N s" is added.
4. **One action.** This is Retry or a navigation link.
5. **"Reference: <request_id>"** in small monospace type, with a Copy button, when the API sent a request ID.

`role="alert"` is used only when the error replaces the page's content. An error inside a page that still shows its form or list uses `inline`, which makes it a polite live region. A `VALIDATION_ERROR` with `details` is shown on the fields, not in ErrorState.

## Entries

| Code | HTTP | What happened | What to do next |
| --- | --- | --- | --- |
| `UNAUTHENTICATED` | 401 | You are signed out | Sign in again to continue. Your saved trips are kept. |
| `NOT_FOUND` | 404 | We could not find that | It may have been deleted or belong to another account. Go back to your trips. |
| `STALE_PLAN` | 409 | This plan changed somewhere else | Reload to see the latest version, then make your change again. |
| `GENERATION_IN_PROGRESS` | 409 | An itinerary is still being generated | Wait for it to finish, then try again. |
| `CONFLICT` | 409 | This change conflicts with the trip's current state | Reload the page to see the current state, then try again. |
| `VALIDATION_ERROR` | 422 | Some details need attention | Check the highlighted fields and try again. |
| `INVALID_EDIT` | 422 | That change cannot be made | Choose another day, position or place, or unlock the item first. |
| `RATE_LIMITED` | 429 | Too many requests | Wait a moment, then try again. (Adds "Try again in N s" from `retry_after_s`.) |
| `AI_QUOTA_REACHED` | 429 | Today's AI planning limit is reached | Try again tomorrow, or use the rule-based plan now. |
| `INTERNAL` | 500 | Something went wrong on our side | Try again. If it keeps happening, share the reference below with the team. |
| `NOT_IMPLEMENTED` | 501 | This feature is not available yet | Go back and continue with the rest of your trip. |
| `SERVICE_UNAVAILABLE` | 503 | The service is temporarily unavailable | Try again in a few minutes. Your saved work is kept. |
| network error | none | The server could not be reached | Check your connection and try again; your input is kept. |

`NOT_IMPLEMENTED` is temporary: §6.3 says no MVP route returns it after SG-6. It is listed because it is a §6.3 code and the generated `ErrorCode` type includes it.
