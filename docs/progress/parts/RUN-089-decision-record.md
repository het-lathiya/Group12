# RUN-089 · decision-record part (IMD-216)

- Part: record IMD-216 (the team's answers to the Amendment A2 proposed decisions PD-A2-1 to PD-A2-7) and update the A2 lines it changes (0 points)
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-216; amends Amendment A2 (IMD-210) for PD-A2-5; keeps IMD-05, IMD-11, IMD-47, IMD-128, IMD-215

## Changed files

- `docs/spec/DECISION_REGISTER.md`: row IMD-216 appended after IMD-215 in the confirmed decisions table, same format, dated 23 November 2026, "decided by: team (via operator Nidhi)".
- `docs/spec/AMENDMENT_A2_ANY_CITY.md`, only the lines IMD-216 changes:
  - status line under the header: "Updated 23 Nov 2026 by IMD-216.";
  - §1.2: the last bullet (multi-zone countries and non-two-decimal currencies cut) deleted;
  - §1.3: the "Multi-zone countries" row deleted;
  - §6.1: the "Country table" bullet rewritten per PD-A2-5 (every country; nearest `zone1970.tab` point for multi-zone countries; any ISO 4217 code with money kept at two decimals; 422 only for a code missing from the table);
  - IMP-724 step 5 and the acceptance bullet on currencies;
  - TC-464 text;
  - §15 rows 4 and 49, "Required change" column.
- `docs/progress/parts/RUN-089-decision-record.md` (this record).

## What IMD-216 says

PD-A2-1 (token `!any_city_mode`), PD-A2-2 (router mounted only when ON, separate any-city contract), PD-A2-3 (`WIKI_USER_AGENT` reused for Nominatim, Overpass and MediaWiki), PD-A2-4 (no opening hours for live places in C-lite), PD-A2-6 (C1 split into C1a on 23 November and C1b on 24 November) and PD-A2-7 (NFR-051 stays proposed until measured) are agreed as written. PD-A2-5 is changed: every country is supported, multi-zone countries take the zone of the nearest representative point of `zone1970.tab`, any ISO 4217 currency is accepted with money kept at two decimals (IMD-05), and "This country is not supported yet" remains only for a country code missing from the table.

## Acceptance

- IMD-216 is in the register's existing format with the date and "decided by" text of the run prompt: **verified** by reading the row after the edit.
- Only the A2 lines named by the run prompt changed: **verified** with `git diff --stat` (A2: 8 insertions, 8 deletions; register: 1 insertion) and by reading the diff.
- No code changed in this part: **verified** (`git diff --stat` lists the two documents and this record only).

## Commands

| Command | Result line |
| --- | --- |
| `git diff --check` | no output (exit 0) |

`make check` and the attribution checks ran once on the branch head; their result lines are in the SYNC REPORT of RUN-089 and in `IMP-722-whole-task.md`.

## Proposed decisions (not decided; for the team)

- **PD-IMP-799-2** (from RUN-087) stays open: `.github/workflows/live-smoke.yml` does not exist, so the SG-7 live smoke has no workflow. It is not recorded as a decision in this run (operator correction to RUN-089).

## Blockers and open issues

none
