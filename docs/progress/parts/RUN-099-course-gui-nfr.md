# RUN-099 · IMD-221 · GUI and non-functional testing

Owner: Krrish (`Krrish Kamani`). Base: `77e52bac363b91b578e7636bcf6833b2e90fb5e4`.

Changed: `docs/course/07-gui-testing.md`, `09-non-functional-testing.md`,
`docs/test-reports/course/baseline-ci-summary.txt` and this record.

The GUI report maps actual Playwright spec files, journeys and tags, distinguishes the axe helpers'
critical/serious handling, and gives an unchecked demo checklist. The NFR report maps latency, limits,
authorization/audit, privacy, accessibility and fallback evidence to existing NFR/TC IDs. Targets and
unobserved deployment metrics stay unverified; the gate record is not changed.

Source: [baseline E2E](https://github.com/het-lathiya/Group12/actions/runs/45678353192) and
[baseline CI](https://github.com/het-lathiya/Group12/actions/runs/45678355628), both `77e52ba`,
conclusion `success`. Logs downloaded with `gh api repos/het-lathiya/Group12/actions/jobs/<job-id>/logs`;
only summary lines were extracted into the tracked text file.

| Executed evidence | Exact result line |
| --- | --- |
| E2E journey | `4 passed (42.0s)` |
| E2E map | `8 passed (21.3s)` |
| E2E editing and restore | `8 passed (52.0s)` |
| E2E regression | `9 skipped`; `12 passed (24.4s)` |
| E2E floor | `1 passed (15.0s)` |
| E2E timeout | `1 skipped`; `1 passed (6.7s)` |
| E2E quota | `1 skipped`; `1 passed (7.6s)` |
| FAKE/MOCK any-city E2E | `4 passed (14.4s)` |
| CI authorization | `91 passed, 14 skipped, 1 warning in 48.61s` |
| CI guards | `496 commits scanned.`; `no leaks found` |
| CI project API audit | `No known vulnerabilities found` |
| CI web audit | `11 moderate severity vulnerabilities` |
| CI installer-only audit | `Found 12 known vulnerabilities in 1 package` |

Validation: spec/tag/helper names checked against `apps/web/e2e/`, workflow commands, implementation
NFR register and downloaded logs. Coverage/tool code is validated in the other owner records.
No source tests or UI changed in this part. `git diff --check`: exit 0.

Acceptance: spec/journey/tag inventory, accessibility explanation, baseline run/result provenance,
manual checklist and NFR evidence/limitations documented. Manual GUI, live/staging, load/performance,
device and deployed-security checks: not run — pending staging window 1 Dec.
Local `make check`/E2E: not run — operator fast mode; CI covers.
No contracts or migrations changed.
