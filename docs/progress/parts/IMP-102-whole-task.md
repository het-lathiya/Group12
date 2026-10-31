# IMP-102 · whole-task part

- Run id: RUN-003
- Owner: Kirtan (kirtan-S111)
- Status: PR_OPEN
- Base commit: 4e4a7fe
- Branch: feat/IMP-102-whole-task
- Reviewer: Junaid (Junaid-Kureshi)
- Traces to: US-001; NFR-013, NFR-018, NFR-031, NFR-034, NFR-048
- Card steps built: 1 to 6, and step 7 limited to the collaborator check and `docs/progress/board-issues.md`. Step 8 (branch protection, merge setting, the `TEAM_EMAILS` variable, screenshot) is done by the repository admin after this run; the board and its issues are not created in this run.

## Changed files

- `.github/workflows/ci.yml` (created)
- `.githooks/commit-msg` (created, mode 100755)
- `scripts/check_attribution.sh` (created, mode 100755)
- `.github/pull_request_template.md` (created)
- `.github/CODEOWNERS` (created)
- `docs/guides/contributing.md` (created)
- `docs/progress/board-issues.md` (created)
- This record (created)

No `.gitleaks.toml` was added: gitleaks found nothing in `docs/spec` or anywhere else (commands below), so no allowlist is needed. The Makefile was not changed; `make setup` already sets `core.hooksPath` to `.githooks` now that the directory exists.

## What the files contain

**ci.yml.** Triggers: `pull_request` (types opened, synchronize, reopened, edited, so a body edit re-runs the attribution check) and `push` to `main`. `permissions: contents: read, pull-requests: read`; no secret other than the default `GITHUB_TOKEN`; workflow env `AI_PROVIDER=MOCK`, `APP_ENV=test`. Python 3.12 through `actions/setup-python@v7` (pip cache keyed on `apps/api/pyproject.toml`), Node from `.nvmrc` through `actions/setup-node@v7` (npm cache keyed on `apps/web/package-lock.json`); every job that needs the toolchains installs with `make setup`.

| Job | Trigger | Steps |
| --- | --- | --- |
| `lint-types` | PR and push to main | `make lint`, `make typecheck`, `make imports` |
| `unit` | PR and push to main | `make test-unit`, `make test-contract`, `make test-web` |
| `guards` | PR and push to main | gitleaks 8.30.1 (release archive, sha256 pinned in the workflow and checked); PR: `gitleaks git --log-opts="--no-merges <base.sha>..<head.sha>"` from the payload; push to main: the full history |
| `attribution` | PR only | `bash scripts/check_attribution.sh` with `TEAM_EMAILS: ${{ vars.TEAM_EMAILS }}`, checkout with `fetch-depth: 0` |
| `audit` | PR and push to main | pip-audit of the installed API dependencies (any finding fails); pip-audit of the venv's own installer, report only; `npm audit --audit-level=critical` in `apps/web` |
| `api` | PR and push to main | service `postgres:16` (database `travel_test`, health check `pg_isready`); `TEST_DATABASE_URL` and `DATABASE_URL` set to the §4.7 default `postgresql+psycopg://postgres:postgres@localhost:5432/travel_test`; `make db-migrate`, `make test-api`, `make test-authz` |

**.githooks/commit-msg** (POSIX sh). Removes `CLAUDE.md` and `.claude/` in any case, then rejects, case-insensitively, a line that starts with `co-authored-by:` (leading spaces allowed; rule `co-authored-by`) or one of the two forbidden tool words of card step 4 as a whole word (rule `tool-word`; word edges as perl `\b`, so `claude_code` and `claudette` are not whole-word matches). It prints `commit-msg: rule <name> failed: ...` and exits 1.

**scripts/check_attribution.sh** (bash). Reads `pull_request.base.sha`, `pull_request.head.sha` and `pull_request.body` from `$GITHUB_EVENT_PATH` (python3, present on the runner and on every member's machine; jq is not installed locally), never `HEAD`. For each commit of `git rev-list --no-merges <base>..<head>` it reports rule `team-email` (author email not in `TEAM_EMAILS`, compared without case; commas, spaces, semicolons or new lines separate the list), rule `committer` (committer name or email differs from the author) and the rule of the hook, which it runs as is on the message, so both apply the same rules. It then runs the hook on the pull-request body. Each failure prints `attribution: FAIL commit <sha7> rule <name> failed: ...` (emails are never printed); the last line is `attribution: PASS <n> commit(s) of <base7>..<head7> and the pull request body` or `attribution: FAIL <k> problem(s) in ...`. Exit 0 pass, 1 rule failure, 2 unusable input (empty `TEAM_EMAILS`, missing payload, commits not in the clone).

**Pull-request template.** Linked IMP task, part and requirement IDs; what changed; tests run with commands and result lines; screenshots; contract and migration checkboxes; part owner, reviewer, part record, prerequisites; checklist. No tool, AI-use or generated-by text; the template passes the hook (exit 0).

**CODEOWNERS.** `/contracts/`, `/apps/api/migrations/`, `/apps/api/app/schemas/` → `@kirtan-S111`; `/apps/api/app/ai/` → `@Nidhi9864`. Kirtan only on the first three: see PD-G.

**contributing.md.** Branch naming, Conventional Commits with the task ID, owner identity with the `-c` pair, one author, the hook and its rules, the two before-push checks of CLAUDE.md §12, pull-request title, assignee and reviewer, the template, API part before screen part, one migration per pull request, the six required checks, Rebase and merge only (IMD-63), the part record per pull request (IMD-62), when a part counts as done.

**board-issues.md.** One row per task part of every card: 183 rows, 108 cards, 427 points (Sprint 1: 21 parts, 47 points; per-member totals 43/42 as in §14.3). Title `IMP-NNN · <part text as written on the card>` or `IMP-NNN · whole task`, GitHub assignee, labels `sprint-N` and `points-X`, status. The two IMP-101 parts are marked `merged`.

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| Preflight: `git fetch origin; git status --porcelain --untracked-files=no` | no output; base `git rev-parse --short origin/main` → `4e4a7fe` |
| Preflight on main: `make lint` / `make typecheck` / `make imports` | exit 0 / exit 0 / `Contracts: 3 kept, 0 broken.` |
| `gh api repos/het-lathiya/Group12/collaborators --jq '.[].login'` | `Manasvi1704`, `Junaid-Kureshi`, `Assassin-byte`, `het-lathiya`, `jeelfefar2141`, `Nidhi9864`, `manyarana`, `Malhar1112-v`, `manalPatel2557`, `kirtan-S111` (all ten) |
| `gh api repos/het-lathiya/Group12/invitations --jq '.[].invitee.login'` | no output (no pending invitation) |
| `gh api repos/het-lathiya/Group12 --jq '{allow_squash_merge,allow_merge_commit,allow_rebase_merge}'` | `{"allow_merge_commit":false,"allow_rebase_merge":true,"allow_squash_merge":false}` |
| `gh variable list` | `TEAM_EMAILS` exists: 10 comma-separated emails, Kirtan's among them (values not printed) |
| gitleaks 8.30.1 (docker image) `gitleaks git --redact` over the full history, before the changes | `23 commits scanned.` `no leaks found` |
| gitleaks over `origin/main..HEAD` (`--log-opts="--no-merges <base>..HEAD"`) and over the full history, after the commits | `no leaks found` (both) |
| `apps/api/.venv/bin/pip-audit` (whole venv) | `Found 12 known vulnerabilities in 1 package` — all in `pip 24.0` (the venv's installer), see open issues |
| `pip freeze --exclude-editable` → `pip-audit --requirement <file> --no-deps --disable-pip` (the CI audit step) | `No known vulnerabilities found` |
| `npm audit --audit-level=critical` (apps/web) | exit 0 (the 16 moderate dev-only findings of RUN-001 do not fail it) |
| `actionlint .github/workflows/ci.yml` (rhysd/actionlint 1.7.12, docker) | no output, exit 0 |
| `shellcheck scripts/check_attribution.sh .githooks/commit-msg` (docker) | no output, exit 0 |
| Hook through git: `git commit --allow-empty -m "<message with the vendor word>"` after `git config core.hooksPath .githooks` | `commit-msg: rule tool-word failed: ...`, exit 1, no commit created |
| `make lint` | `All matched files use Prettier code style!` (exit 0; ruff `All checks passed!`) |
| `make typecheck` | `✓ Types generated successfully` (exit 0; mypy `Success: no issues found in 13 source files`) |
| `make imports` | `Contracts: 3 kept, 0 broken.` |
| `make test` | `No test files found, exiting with code 0` (exit 0; API unit `20 passed in 0.16s`; contract, api, authz `pytest: no tests collected (exit 5 treated as success)`) |
| `make check` | `No test files found, exiting with code 0` (exit 0) |

### Hook test (IMD-61, local half)

Message files in a scratch directory outside the repository, passed to `.githooks/commit-msg` directly.

| Message | Exit | Printed rule |
| --- | --- | --- |
| Subject plus a `Co-authored-by: Someone <...>` trailer | 1 | `commit-msg: rule co-authored-by failed: a line starts with 'Co-authored-by:' (one author per commit, IMD-61).` |
| Subject naming the tool word, capitalised | 1 | `commit-msg: rule tool-word failed: the message names an AI tool or its vendor (IMD-61); only the paths CLAUDE.md and .claude/ may appear.` |
| Body naming the tool word followed by "code", lower case | 1 | `commit-msg: rule tool-word failed: ...` |
| Vendor word in upper case | 1 | `commit-msg: rule tool-word failed: ...` |
| Indented trailer in mixed case (`  co-AUTHORED-by: ...`) | 1 | `commit-msg: rule co-authored-by failed: ...` |
| Only `CLAUDE.md` and `.claude/settings.json` | 0 | none |
| `claude.md` and `.CLAUDE/` in other cases | 0 | none |
| The word `claudette` | 0 | none |
| An identifier `claude_code` (underscore joins the word, as perl `\b`) | 0 | none |

### Attribution script test (IMD-61, CI half)

A scratch repository in the scratchpad (outside the repository, no remote, never pushed); one branch per case from a base commit; a payload file per case with `pull_request.base.sha`, `head.sha` and `body`; `TEAM_EMAILS` set from the repository variable (the ten team emails).

| Case | Exit | Result lines |
| --- | --- | --- |
| Clean commit by Kirtan, clean body | 0 | `attribution: PASS 1 commit(s) of 12369af..a5d23e0 and the pull request body` |
| Message with a `Co-authored-by:` trailer | 1 | `attribution: FAIL commit a4d22f6 rule co-authored-by failed: a line starts with 'Co-authored-by:' (one author per commit, IMD-61).` |
| Author and committer `outsider@example.com` | 1 | `attribution: FAIL commit ea6bb88 rule team-email failed: the author email is not in TEAM_EMAILS` |
| Author Kirtan, committer `GitHub <noreply@github.com>` | 1 | `attribution: FAIL commit edb6488 rule committer failed: the committer differs from the author (author and commit as the part owner)` |
| Clean commit, body (CRLF lines) naming the tool | 1 | `attribution: FAIL pull request body rule tool-word failed: the message names an AI tool or its vendor (IMD-61); only the paths CLAUDE.md and .claude/ may appear.` |
| Clean commit, empty `TEAM_EMAILS` | 2 | `attribution: ERROR TEAM_EMAILS is empty; set the repository variable TEAM_EMAILS (comma-separated)` |
| Clean commit, `null` body | 0 | `attribution: PASS ...` |
| Clean commit, `TEAM_EMAILS` upper case with ` ; ` separators | 0 | `attribution: PASS ...` |

Each failing case also prints the summary `attribution: FAIL 1 problem(s) in 1 commit(s) of <base7>..<head7> and the pull request body`.

### TC-002 (local half)

Scratch copy of `apps/api/app` and `.importlinter` outside the repository, with `from google import genai` planted in `app/itinerary/service.py`; `lint-imports --config .importlinter`:

`Contracts: 2 kept, 1 broken.` — broken: `Vendor isolation: google (google.genai) only in app.ai.providers.gemini`, `app.itinerary.service -> google (l.1)`; exit 1.

### CI on the pull request

Pull request https://github.com/het-lathiya/Group12/pull/3, workflow run https://github.com/het-lathiya/Group12/actions/runs/41223146687 (head `958a414`, the six commits before this record was updated). `gh pr checks 3`:

| Job | Conclusion | Job URL | Result line from the log |
| --- | --- | --- | --- |
| `lint-types` | pass (1m39s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692156 | `Contracts: 3 kept, 0 broken.` (also `All checks passed!`, `Success: no issues found in 13 source files`, `All matched files use Prettier code style!`) |
| `unit` | pass (1m36s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692102 | `20 passed in 0.16s`; contract `pytest: no tests collected (exit 5 treated as success)`; web `No test files found, exiting with code 0` |
| `guards` | pass (7s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692264 | `6 commits scanned.` `no leaks found` |
| `attribution` | pass (5s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692047 | `attribution: PASS 6 commit(s) of 4e4a7fe..958a414 and the pull request body` |
| `audit` | pass (1m38s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692212 | `No known vulnerabilities found` (API dependencies); report-only step `Found 12 known vulnerabilities in 1 package` (the venv's `pip 25.0.1`); npm `16 moderate severity vulnerabilities`, exit 0 at `--audit-level=critical` |
| `api` | pass (1m41s) | https://github.com/het-lathiya/Group12/actions/runs/41223146687/job/124601692325 | `db-migrate: not yet implemented (IMP-106)`; api and authz `pytest: no tests collected (exit 5 treated as success)` |

CI used Python 3.12.15 (`python-version: "3.12"`); `.python-version` pins 3.12.3 locally. The commit that adds these results starts a new run on the same pull request.

## Not run

| Command | Reason |
| --- | --- |
| Throw-away pull requests for TC-343 (failing test) and TC-354 (fake secret) | After branch protection (admin step); not opened in this run |
| Attribution negative test on a pull request (`test/attribution-check`) | Done by the operator by hand after branch protection, as the card says |
| `make db-migrate` against a real database (TC-337) | `db-migrate: not yet implemented (IMP-106)`; the `api` job runs it and becomes meaningful after IMP-106 |
| `make openapi-check` in the guards job (§13.7) | `not yet implemented (IMP-214)`; IMP-214 extends ci.yml with it (§4.1) |
| `ci.yml` build job (§13.7, TC-338) | Not in this card's six jobs; it comes with the deployment card |
| Board creation and issue import | Not in this run; the list is `docs/progress/board-issues.md` |
| `make e2e` | The part touches no journey |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Hook refuses a `Co-authored-by:` message and the tool and vendor words; accepts the allowed paths (IMD-61, local half) | verified | Hook test table above; also refused through `git commit` with `core.hooksPath=.githooks` |
| Attribution check fails on a `Co-authored-by:` line, a non-team author email, a different committer and a forbidden word in the body; passes a clean team commit (IMD-61, CI half, local run) | verified | Attribution script table above |
| TC-002: a `google.genai` import outside `app/ai/providers/gemini.py` fails `make imports` (local half) | verified | Scratch-copy run above: `Contracts: 2 kept, 1 broken.` |
| The six jobs exist with the exact names and are green on this pull request, attribution included | verified | Run 41223146687: all six `pass` (table above) |
| Repository merge settings: Rebase and merge only | verified (API output; screenshot after the admin step) | `{"allow_merge_commit":false,"allow_rebase_merge":true,"allow_squash_merge":false}` |
| All ten members are collaborators | verified | collaborator list above; no pending invitations |
| Board holds one issue per task part | not verified | List generated (183 rows); board not created in this run |
| TC-343: a failing unit test gives a red required check and blocks merge | not verified | Needs branch protection and a throw-away pull request (after this run) |
| TC-354: a fake key fails the guards job | not verified | Same; gitleaks runs in `guards` |
| Attribution negative test on a real pull request | not verified | Operator's manual test after branch protection |
| Branch protection settings match step 8 | not verified | Admin step after this run |
| TC-337: the api job applies migrations to a blank PostgreSQL | not verified | Meaningful after IMP-106 |

## Blockers

None.

## Proposed decisions

- PD-G (CODEOWNERS second owner): §14.4 and card step 5 ask for "Kirtan plus one other owner" on `contracts/`, `apps/api/migrations/` and `apps/api/app/schemas/`. CODEOWNERS cannot require two approvals from listed owners (any one listed owner satisfies it) and the specification names no second owner, so only Kirtan is listed. Options for the team: name a second owner and require two approvals in branch protection for those paths by agreement, or accept one code-owner approval plus the named reviewer.
- PD-H (pip-audit scope): the blocking audit covers every installed API dependency (runtime and dev) at its installed version, taken from `pip freeze --exclude-editable`; it leaves out the venv's own `pip`, which `python -m venv` copies from the interpreter and which is not a project dependency. The venv's `pip` is audited in a report-only step so the finding stays visible. Making it blocking needs `make setup` to upgrade pip in the venv (for example `python -m venv --upgrade-deps`), a Makefile change outside this part.
- PD-I (attribution rule wording): the hook and CI script apply card step 4 exactly (a line starting with `co-authored-by:`; the two tool words as whole words). The before-push perl check of CLAUDE.md §12 is broader (it also flags `co-authored-by` anywhere in a line, and the vendor word inside longer words). Anything that passes the perl check passes the hook, so there is no conflict in practice; the team may align the wording in a decision run.
- PD-J (`api` job database URL): `make db-migrate` reads `DATABASE_URL` (§4.7), so the job sets both `DATABASE_URL` and `TEST_DATABASE_URL` to the §4.7 test default. No variable name is new.

## Open issues

- pip-audit of the whole venv reports 12 advisories in its own `pip` (locally `pip 24.0`, in CI `pip 25.0.1`; IDs PYSEC-2026-1795, -1796, -196, -2875, -2876, -3721; fixed in pip 25.3 to 26.2). The project dependencies have none. See PD-H.
- `unit` also runs `make test-contract` (§13.7 lists it; the card step lists `make test-unit` and `make test-web`). §13.7's coverage report is not added: no coverage tool is in the dependencies.
- `guards` does not repeat `make imports`: the provider-isolation import rule already runs in `lint-types` as `make imports`.
- The `edited` trigger re-runs every job when the title or body of a pull request changes; it is what lets the attribution check see body edits.
- `git commit -v` passes the diff to the hook; a diff line containing a tool word would then be refused. Commit without `-v` or reword.
- CODEOWNERS reviews are enforced only when the admin enables "Require review from Code Owners" in branch protection; card step 8 does not list it, so it is in the after-this-run list.
- The pull request is opened from the operator's GitHub account (`het-lathiya`); the commits are authored and committed by Kirtan.

## After this run

1. Repository admin: branch protection on `main` (pull request required, one approval, required checks `lint-types`, `unit`, `guards`, `attribution`, `audit`, `api`, linear history, no force push; also "Require review from Code Owners" if the team wants CODEOWNERS enforced); confirm Rebase and merge only; confirm the `TEAM_EMAILS` variable; record the screenshots (branch protection in `docs/progress/sprint-1.md`, merge settings in this record).
2. Throw-away pull requests: one with a failing unit test (TC-343) and one with a fake key (TC-354); both must be red, then closed unmerged.
3. Operator's attribution negative test: branch `test/attribution-check`, a commit made with `--no-verify` that has a `Co-authored-by:` line; the attribution check must be red; close the pull request and delete the branch.
4. Board: `gh auth refresh -s project`, create the labels and the GitHub Projects board, import the 183 issues of `docs/progress/board-issues.md`, record a screenshot or export in `docs/progress/sprint-1.md`.
