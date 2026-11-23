# IMP-733 · environment part (any-city environment and switch documentation)

- Card: IMP-733 Documents: acceptance record, guides, report addendum and environment (Amendment A2 §7.2, §12 Batch C3; 0 points)
- Part: environment (documentation only)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Kirtan
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: A2 §3.1, §7.2, §7.3; IMD-12, IMD-102, IMD-217

## Changed files

- `docs/guides/deployment.md`: section 10, the any-city mode addendum:
  - the switch token in `STAGING_FEATURES_DISABLED` and the web build argument;
  - the §7.2 variables with defaults and staging values;
  - `LIVE_DATA_PROVIDER=LIVE`, and `WIKI_USER_AGENT` = "<to be set by Kirtan: app name + team contact>";
  - one API task while ON;
  - the pre-import CLI and rollback (remove the token).
- `.env.example`:
  - a comment on `WIKI_USER_AGENT`;
  - a new "any-city live data" block with `LIVE_DATA_PROVIDER=FAKE` and the §7.2 names at their defaults, with comments.
  No value is a secret, and names and defaults are as in `app/core/config.py`.

No `infra/` template and no workflow changed.

## Commands

| Command | Result line |
| --- | --- |
| `make check` on the head (covers `tests/unit/core/test_config.py`, including `test_defaults_follow_env_example`) | see the SYNC REPORT of RUN-092 |

## Acceptance

- The A2 §7.2 names and defaults are documented, and `.env.example` holds names with default or placeholder values only: **verified** by comparing with `app/core/config.py` lines 94 to 103.
- Nothing in `infra/` or the workflows changed in this part: **verified** (`git diff --stat`: `.env.example`, `docs/guides/deployment.md` and this record).

## Proposed decisions

none

## Open issues

- `WIKI_USER_AGENT` for staging: Kirtan sets the app name and team contact.
- Adding the live-data variables to `infra/aws/services/api.staging.json.tmpl` is Kirtan's change in the staging window, only if the switch is ON at the cutoff.

## Blockers

none
