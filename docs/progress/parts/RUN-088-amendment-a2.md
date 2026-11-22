# RUN-088 · amendment-a2 part (Amendment A2 and code impact survey)

- Part: Amendment A2 any-city mode, code impact survey, source proposal copy, CLAUDE.md source line (0 points)
- Run id: RUN-088 (Batch E0, Sprint 7, inserted)
- Owner: Het (Het Lathiya)
- Status: PR_OPEN candidate on `chore/S7-E0-any-city-a2`
- Base commit: c23d78b (on `main`)
- Traces to: IMD-210, IMD-215

## Changed files

- `docs/spec/AMENDMENT_A2_ANY_CITY.md` (create)
- `docs/proposals/any-city-plan-option-c.md` (create: verbatim copy of the Option C plan, with the first line "Source proposal; superseded where Amendment A2 differs")
- `CLAUDE.md` (one line: A2 added to the sources of truth, ranked like A1)
- `docs/progress/parts/RUN-088-amendment-a2.md` (this record)

## What A2 fixes

- **Switch name:** `any_city_mode`, a default-off switch in the existing `FEATURES_DISABLED` / `NEXT_PUBLIC_FEATURES_DISABLED`. Only the token `!any_city_mode` turns it ON.
- **Routes:** mounted only when the switch is ON, with a separate any-city contract.
- **Migration:** `0008_live_destinations` only adds columns to `destinations`, so the drift test code is unchanged.
- **New API:** API-76 to API-79.
- **New module:** MOD-B19 `app/livedata/`.
- **New IDs:** FR-141 to FR-145, NFR-051 to NFR-052, TC-460 to TC-491, ACC-20 to ACC-23, E2E-10, CHK-26, C-14.
- **Cards:** IMP-721 to IMP-733, all 0 points.
  - C1: IMP-721 (Malhar, Jeel), IMP-722 (Het), IMP-723 (Manal, Junaid), IMP-724 (Jeel, Malhar), IMP-725 (Het, Manal).
  - C2: IMP-726 (Nidhi), IMP-727 (Manya), IMP-728 (Manasvi), IMP-729 (Krrish).
  - C3: IMP-730 (Krrish), IMP-731 (Junaid), IMP-732 (Manya), IMP-733 (Nidhi, with Kirtan for env/SSM docs).

## Survey findings by area (93)

Findings by area, 93 in all:

| Area | Count |
| --- | --- |
| data model | 11 |
| RAG | 9 |
| tests/CI | 8 |
| API | 6 |
| destination/seed | 6 |
| providers | 6 |
| settings/switch | 6 |
| jobs | 5 |
| ranking/filters | 5 |
| schemas | 5 |
| security | 4 |
| web trip form | 4 |
| budget | 3 |
| eval | 3 |
| prompt | 3 |
| web search/explore | 3 |
| fallback planner | 2 |
| validation | 2 |
| web costs | 1 |
| web map | 1 |

By batch: C1 56, C2 28, C3 9.

## Stop-condition gaps (recorded; A2 written with each resolved)

- **Switch mechanism.** It is a disable list where an empty value means ON. A2 §3.1 resolves this with a token.
- **Job runner.** It is generation-specific (`ai_generations`). A2 §6.2 resolves this with import state on `destinations` and a separate runner.

## Open questions

- **Production template:** there is no production task template in `infra/aws/services/`. Question for Kirtan.
- **Gemini quota:** live imports use embedding quota on the free key.
- **Single process:** the outbound limit holds only per process (IMD-12, one ECS task).
- **Usage policies:** the Nominatim, Overpass and OSM policies are Unverified until IMP-723 records them (A2 §16).
- **CLAUDE.md wording:** §4 rule 2 (the MediaWiki client path) and §8 (members write guides) are superseded by A2 for any-city mode. Rewording them is left to IMP-733.

## Proposed decisions

- **PD-A2-1:** confirm the `!any_city_mode` token syntax.
- **PD-A2-2:** confirm conditional route mounting and the separate any-city contract file.
- **PD-A2-3:** reuse `WIKI_USER_AGENT` for every OSM and MediaWiki call.
- **PD-A2-4:** live places have no opening hours in C-lite.
- **PD-A2-5:** support only two-decimal currencies and countries whose time zone can be decided.
- **PD-A2-6:** split C1 into C1a (23 Nov) and C1b (24 Nov).
- **PD-A2-7:** NFR-051 target is a proposed value until measured.

## Commands

Run once on the branch with both RUN-088 parts (local Supabase stack and compose test database; MOCK provider).

| Command | Result line |
| --- | --- |
| `make lint` | `All checks passed!` · `236 files already formatted` · `All matched files use Prettier code style!` |
| `make check` | exit 0: `Success: no issues found in 123 source files` · `Contracts: 6 kept, 0 broken.` · `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` · `1219 passed, 1 warning in 7.87s` · `91 passed, 2 deselected, 1 warning in 18.42s` · `590 passed, 1 warning in 109.67s (0:01:49)` · `87 passed, 14 skipped, 1 warning in 21.39s` · `Tests  288 passed (288)` |
| `make guards` | not run: the Makefile has no `guards` target (CI job `guards` runs on the pull request) |
| attribution checks (`git log origin/main..HEAD …`) | each commit has its owner as author and committer; the wording check prints nothing |

Docs only: no code, test, contract, migration, workflow or Makefile change.
