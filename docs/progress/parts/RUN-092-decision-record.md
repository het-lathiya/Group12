# RUN-092 · decision-record part (IMD-218)

- Part: record IMD-218, the team's answer to PD-726-1 (RUN-091), with a note on TC-480 for quota (0 points)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: IMD-218; reads Amendment A2 §6.2 and §6.5; keeps IMD-44, IMD-112, IMD-217

## Changed files

- `docs/spec/DECISION_REGISTER.md`: row IMD-218 appended after IMD-217 in the confirmed decisions table, same format, dated 23 November 2026, "decided by: team (via operator Nidhi)".
- `docs/progress/parts/RUN-092-decision-record.md` (this record).

## What IMD-218 says

- **PD-726-1 agreed.** If the guide source (Wikivoyage or Wikipedia) fails during a live import:
  - the places are stored;
  - the import completes without guide documents;
  - generation runs with no guide citations;
  - the failure is logged with the destination id only.
  A2 §6.2's error list covers the places provider. The code of IMP-726 (`rag.service.fetch_live_guides`) already behaves like this, and `test_live_guides_source_failure_stores_places_without_guides` shows it.
- **Note on TC-480 for quota.** Quota follows IMD-44: the generation ends `failed` with the rule-based option, and that option then yields the rule-based plan. This is how `test_live_generation_tc_480_quota_fails_with_the_rule_based_option_which_plans` verifies it.

## Acceptance

- IMD-218 is in the register's existing format, with the date and "decided by" text of the run prompt: **verified** by reading the row after the edit.
- No code and no amendment text changed in this part: **verified** (`git diff --stat` lists the register, with 1 insertion, and this record).

## Commands

| Command | Result line |
| --- | --- |
| `git diff --check` | no output (exit 0) |

`make check` and the attribution checks ran once on the branch head. Their lines are in the SYNC REPORT of RUN-092.

## Proposed decisions

none (PD-IMP-799-2 from RUN-087 stays open and is not recorded)

## Blockers and open issues

none
