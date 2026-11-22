# RUN-088 · decision-record part (IMD-210, IMD-215)

- Part: record IMD-210 (any-city mode, scope "C-lite") and IMD-215 (feature-freeze exception and schedule) (0 points)
- Run id: RUN-088 (Batch E0, Sprint 7, inserted)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `chore/S7-E0-any-city-a2`
- Base commit: c23d78b (on `main`)
- Traces to: IMD-210, IMD-215; amends IMD-201 (freeze) for the IMD-210 work only; keeps IMD-11, IMD-33, IMD-47, IMD-65, IMD-107, IMD-112, IMD-128; source proposal `docs/proposals/any-city-plan-option-c.md` (added by the Amendment A2 part of this run)

## Changed files

- `docs/spec/DECISION_REGISTER.md`: rows IMD-210 and IMD-215 appended after IMD-214 in the confirmed decisions table, same format, dated 22 November 2026, "decided by: team (via operator Nidhi)".
- `docs/progress/parts/RUN-088-decision-record.md` (this record).

## What the rows say

- **IMD-210.** Any-city mode adopted as scope "C-lite" of the Option C plan, with the kept items, the cut list (function-calling planner, Firecrawl, Google Maps or Search grounding, paid Gemini key, LLM-as-judge), 0 points outside the contribution plan, and acceptance (a) to (e). The design, names and cards are in Amendment A2 (`docs/spec/AMENDMENT_A2_ANY_CITY.md`), written by the second part of this run.
- **IMD-215.** The IMD-201 freeze is lifted for the IMD-210 work only, until 27 November 2026 23:59 IST; one switch, OFF by default, with the existing mechanism (name fixed in Amendment A2); switch-OFF release if the batches are not green with the switch OFF and ON by the cutoff; one staging window on the final candidate on 28 November 2026 (Kirtan); SG-7 close and `v1.0-rc1` on 29 November 2026 if the criteria hold; afterwards only severity 1 and 2 fixes; batches E0, C1, C2, C3.

## Acceptance

- IMD-210 and IMD-215 are in the register's existing format with the date and "decided by" text of the run prompt: **verified** by reading the rows after the edit.
- No other register row, no specification file and no code changed in this part: **verified** with `git diff --stat` (one file, 2 insertions, before this record was added).

## Commands

| Command | Result line |
| --- | --- |
| `git diff --check` | no output (exit 0) |
| `make lint` | `All checks passed!` · `236 files already formatted` · `All matched files use Prettier code style!` |

`make check` and the attribution checks ran once on the branch head; their result lines are in `RUN-088-amendment-a2.md`.

## Proposed decisions (not decided; for the team)

- **PD-AC-1.** IMP-603 (destination 2) is met by the live tier: a pre-imported live city stands in for the second curated destination. Points to be decided (IMP-603's 5 points stay pending until then; the any-city work itself is 0 points under IMD-210).
- **PD-AC-2.** Demo cities to pre-import in the 28 November staging window. Planner default: Jaipur, Udaipur and Mumbai, plus one small town for the "not enough data" path.
- **PD-IMP-799-2** (from RUN-087) is still open: `.github/workflows/live-smoke.yml` does not exist, so the SG-7 live smoke has no workflow. Amendment A2 gives the any-city `@live` subset; the team still has to decide how the live smoke runs.

## Blockers and open issues

none
