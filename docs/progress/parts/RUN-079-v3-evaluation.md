# RUN-079 · v3-evaluation part (prompt v3 on MOCK and Gemini from main)

- Part: MOCK v2, MOCK v3 and one Gemini v3 evaluation over trips/v1; IMD-195 gate verdict (0 points)
- Run id: RUN-079
- Owner: Manya (Manya Rana)
- Status: PR_OPEN candidate on `chore/S6-E-v3-eval`
- Base commit: 3a68439 (on `main`)
- Traces to: IMD-195, IMD-199, IMD-176, IMD-180, IMD-181, IMD-188

## Changed files

- `eval/results/20261116T042221Z-mock/`, `eval/results/20261116T042224Z-mock/`, `eval/results/20261116T042246Z-gemini/`: `run.json` and `scores.json`, copied unchanged from the clean evaluation worktree at BASE. `raw/` is not committed, as for earlier runs.
- `eval/reports/RUN-079-prompt-v3.md`: commands, records, tables and gate verdict.
- `docs/progress/parts/RUN-079-v3-evaluation.md` (this record).

## Runs

| Run id | Provider | Prompt (record) | Schema-valid | Valid IDs | Usable | Avg travel | Failures | Duplicate items | AI-written |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261116T042221Z-mock | MOCK | v2 | 45/45 | 45/45 | 45/45 | 126.7 | 0 | 0 | 0 |
| 20261116T042224Z-mock | MOCK | v3 | 45/45 | 45/45 | 45/45 | 126.7 | 0 | 0 | 0 |
| 20261116T042246Z-gemini | GEMINI gemini-3.5-flash-lite | v3 | 44/45 | 44/45 | 44/45 | 112.2 | 1 (trips-v1-012 r3, provider_unavailable) | 14 in 3 attempts | 0 |

## Acceptance

- Three runs from a clean tree at a commit on `main` (IMD-176): **verified**. The worktree was detached at 3a68439 and `git status --porcelain` showed only the new results folders; every record holds that `git_commit`.
- Reports quote the prompt version from the record (IMD-195, IMD-199): **verified** in the report tables (`prompt_version`, `prompt_version_overridden: true`).
- Only one Gemini run: **verified** (20261116T042246Z-gemini).
- IMD-195 gate: **NOT MET**. Gemini v3 wrote 14 duplicate-place items in 3 of 45 attempts. All other conditions hold, so v3 was not activated.

## Commands

The checks used a throwaway local PostgreSQL 16 + pgvector (pgserver, port 55432), stopped and removed afterwards.

- `make lint` → `All matched files use Prettier code style!`
- `make typecheck` → `✓ Types generated successfully`
- `make imports` → `Contracts: 6 kept, 0 broken.`
- `make openapi-check` → `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`
- `make test-unit` → `1204 passed, 1 warning in 26.25s`
- `make test-contract` → `91 passed, 2 deselected, 1 warning in 20.76s`
- `make test-api` → `565 passed, 1 warning in 217.65s (0:03:37)`
- `make test-authz` → `71 passed in 41.99s`
- `make test-web` → `Tests  283 passed (283)`
- `make check` → exit 0 (`565 passed, 1 warning in 188.80s (0:03:08)`, `Tests  283 passed (283)`)

Not run: `make e2e` (v3 not activated, so no journey changed; no local Docker).

## Blockers, proposed decisions, open issues

- PD-RUN-079-1: keep itinerary_generate v3 inactive. Before any new activation attempt, decide between two options. (a) A prompt revision that forbids repeating a place across days, evaluated by the same IMD-195 procedure. (b) Amending the gate to accept duplicates that the validator rejects (`rejected_items` equals `duplicate_places` in all three attempts). Either way, baseline-1 has no duplicate count (metrics v1), so the comparison would need a Gemini v1 run under metrics v2.
