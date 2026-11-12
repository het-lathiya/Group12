# RUN-059 · decision-record part

- Run id: RUN-059 (grouped: decision-record, devops-bundle, token-leeway, destination-404, fallback-wording)
- Owner: Nidhi (Nidhi9864)
- Status: PR open
- Base commit: 8c3997b
- Branch: chore/RUN-059-decisions-and-fixes
- Traces to: IMD-137 to IMD-158 (team decision of 12 November 2026, operator het-lathiya); SG-3 open items

## Changed files

- `docs/spec/DECISION_REGISTER.md`: rows IMD-137 to IMD-158 added at the end of "Confirmed decisions", in the IMD-124..136 format; IMD-134 row gets the IMD-141 note.
- `docs/spec/IMPLEMENTATION_SPEC.md`, `docs/spec/TASK_REGISTER.md`, `docs/spec/AMENDMENT_A1_AWS_RAG.md`: the text the decisions name, listed below. The task cards appear in both the specification (table rows) and the task register (step lists); both copies were changed with the same words.
- `docs/progress/parts/RUN-059-decision-record.md`: this record.

None of IMD-137 to IMD-158 was already in the register (`grep` for each ID and for the PD numbers they cite found no earlier row). The "Unresolved decisions" section is unchanged: none of its items (OD-01 to OD-18) is resolved by these decisions.

## Every changed line

| File | Where | Change | Decision |
| --- | --- | --- | --- |
| DECISION_REGISTER.md | IMD-134 row | Appended "**Amended by IMD-141 (12 November 2026):** IMD-126 replaces the OUTSIDE_TRIP_DATES half of PD-IMP-306-3" | IMD-141 |
| DECISION_REGISTER.md | after IMD-136 | 22 new rows IMD-137 to IMD-158 | all |
| IMPLEMENTATION_SPEC.md | §2 FR-047 AC1 | "three consecutive 503 responses" → "five consecutive 503 responses (IMD-146)" | IMD-146 |
| IMPLEMENTATION_SPEC.md | §6 API-26 Errors row | adds 422 `INVALID_EDIT` for mixed move and retime fields (IMD-156) and 501 for any body that sets `is_locked` until IMP-506 (IMD-158) | IMD-156, IMD-158 |
| IMPLEMENTATION_SPEC.md | §6 "Edit an item (API-26)" example | new line after the example: until IMP-506, this example answers 501 because it sets `is_locked` | IMD-158 |
| IMPLEMENTATION_SPEC.md | §7.6 SourceBadge row | "Curated" for prices (no date, IMD-130), "Curated, checked on <date>" for hours | IMD-130 |
| IMPLEMENTATION_SPEC.md | §8 fallback section ("The itinerary page shows FallbackNotice …") | wording → "…unavailable or its answer failed checks" (IMD-154). This is the §8 copy PD-IMP-403-1 names as the second wording | IMD-154 |
| IMPLEMENTATION_SPEC.md | §9.2 label table | the "Curated, checked on {date}" row split into "Curated" (prices, no date, IMD-130) and "Curated, checked on {date}" (hours) | IMD-130 |
| both | IMP-301 step 3 | wire schema "minus $schema, $id, pattern" → "minus $schema, $id and the numeric, length, count, format and pattern keywords, whose limits are stated in descriptions and enforced by code, IMD-136" | IMD-136 |
| both | IMP-403 step 4 | FallbackNotice text → §7.8 wording (IMD-154); "ErrorState with request_id" → "ErrorState …, whose reference is the generation id because API-23 has no request_id (IMD-155)" | IMD-154, IMD-155 |
| both | IMP-407 step 5 | "schedule.recalculate (IMP-308)" → "the FR-060 times rule in itinerary/edits.py (not schedule.recalculate, which would form an import cycle and undo a retime, IMD-153)" | IMD-153 |
| both | IMP-411 step 3 | "curated carries checked_on date" → "curated prices carry no date and curated hours carry checked_on (IMD-130, IMD-149)" | IMD-149 |
| both | IMP-413 step 3 | numbered §21.4 metrics → the three counts the spec defines (§8.11 steps 1 and 3, §8.12), numbered metrics not computed in v1 (IMD-144) | IMD-144 |
| both | IMP-504, new step 7 | turn on removal undo (`EDIT_UNDO_ENABLED` true in `apps/web/lib/api/queries.ts`) (IMD-157) | IMD-157 |
| both | IMP-506, new step 7 | replace the interim 501 for `is_locked`, including the §6 example (IMD-158) | IMD-158 |
| AMENDMENT_A1_AWS_RAG.md | §4.4 Deploy role trust | three subjects → six (the three named and the three immutable `repo:het-lathiya@185104529/Group12@1436091116:…`), audience `sts.amazonaws.com` | IMD-138 |
| AMENDMENT_A1_AWS_RAG.md | §4.5, before "The container never migrates" | new "Express Mode notes" paragraph: task definition from `deployments[?status=='PRIMARY']`, families `default-group12-<service>-<env>`, `--cli-input-json` from a file, not `file:///dev/stdin` | prompt (A1 §4.5 notes, FIX-IMP-218) |

Already aligned before this run, not changed: §7.5.6 and the §7.8 label table (FallbackNotice wording and "Curated" without a date, IMD-130), §8.4 (breaker opens after 5).

Left as they are (not named by the decisions): IMP-411's objective sentence ("Curated (with date)") and IMP-408 step 4 (undo "when available"). Both read consistently with IMD-149 and IMD-157 together, but a later docs run may tidy them.

## Commands and results

| Command | Result |
| --- | --- |
| `for n in $(seq 137 158); do grep -c "^\| IMD-$n \|" docs/spec/DECISION_REGISTER.md; done` | `1` for every ID |
| `make lint` | `All matched files use Prettier code style!` (ruff and ESLint clean; docs are not linted by this target) |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| IMD-137 to IMD-155 recorded in the IMD-124..136 format | verified | rows in the register; each ID once (command above) |
| Addendum IMD-156 to IMD-158 recorded | verified | same check |
| Named spec text aligned and nothing else | verified | `git diff -U0` shows only the lines in the table |
| Unresolved section: only resolved items moved | verified | no item resolved; section unchanged |

## Blockers

None.

## Proposed decisions

None.
