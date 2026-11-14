# Cut-list checkpoint (week 4, IMP-499)

- Gate: SG-4 (blueprint Gate 3), [gates.md](../progress/gates.md#sg-4-end-of-week-4-core-reliability-blueprint-gate-3-imp-499)
- Run: RUN-064 (IMP-499 whole-task, Kirtan), 14 November 2026
- Gate commit: `ec6973a` (`main`)
- Rule: IMP-499 steps 3 to 5 (task register and specification §11 IMP-499 row); cut order: specification §1 "Floor and cut list" and IMD-47; extensions are already cut (IMD-65)
- Result: **C cannot be computed from the repository.** No cut is applied, and `FEATURES_DISABLED` and `NEXT_PUBLIC_FEATURES_DISABLED` are unchanged. Proposed decision PD-IMP-499-1 below; supervisor to confirm.

## The rule

1. C = story points of the stories completed in Sprints 1 to 4 (planned 203). A half-finished story counts as zero.
2. Points to cut = max(0, 359 − 2C).
3. Zones: C ≥ 180 no cut; 162 ≤ C ≤ 179 team and supervisor decide; C < 162 cuts mandatory; C < 158 even the whole list (43 points) is not enough, and further scope reduction is escalated.
4. Cut order: 1 versions (8), 2 trip_management (5), 3 contingency (1), 4 budget_alerts (3), 5 wishlist (3), 6 alternatives (5), 7 regeneration (10), 8 locks (3), 9 meal_slots (5).

## Why C cannot be computed

The rule counts blueprint story points per story, against a planned total of 203. The repository has no per-story point values.

What was searched (repository only):

- `docs/spec/IMPLEMENTATION_SPEC.md`, `docs/spec/AMENDMENT_A1_AWS_RAG.md`, `docs/spec/TASK_REGISTER.md`, `docs/spec/DECISION_REGISTER.md`, `docs/spec/SPRINT_EXECUTION_GUIDE.md` and `docs/` for "story points", "203", "359 - 2C", and for US-nnn identifiers next to a point value. The only hits are the rule itself (IMP-499 step 3) and §11's statement that "Points are the blueprint story points (about three focused hours each); tasks without a story carry an estimate". The blueprint is not in the repository (as PD-IMP-310-1 and PD-IMP-413-3 found).
- The card points of the task register. They exist per card, but they mix story points with estimates for cards that have no story. They also do not add up to the planned 203: the Sprint 1 to 4 tables total **244** card points over 70 cards. That includes the RAG cards IMP-311 to IMP-318 (23 points, added by Amendment A1) and the gate cards (IMP-399 and IMP-499, 4 points). Taking those out leaves 217, not 203, and no other subset found in the documents gives 203. Card points are therefore not the basis the rule names, and this record does not use them as C.

## Sprint 1 to 4 stories that are not complete

Everything else in Sprints 1 to 4 is merged with its part records (the Sprint 1 to 3 gate records and [sprint-4.md](../progress/sprint-4.md)).

| Story or evidence | Card | State | Owner, due |
| --- | --- | --- | --- |
| US-151 user interviews, round 1 | IMP-114 (HUMAN, 3 card points) | BLOCKED: templates ready on PR #201, interviews not held | Junaid, Krrish; Thu 19 November 2026 |
| FR-036 AC3 saved samples for Ahmedabad (US-058, sample half) | IMP-402 sample-itineraries (IMP-402 has 5 card points) | half-finished: Sampleton samples merged (#270); Ahmedabad waits for two trip inputs | Jeel; no date set |
| Staging-only evidence: TC-370 journey on staging, staging fallback demo with `MOCK_PROVIDER_SCENARIO=timeout`, edit totals on staging, ACC-19, NFR-050 p95, staging RAG index line, `make smoke`, TC-433 to TC-435 | IMP-414 and the SG-3 staging items moved to SG-4 | not verifiable until the staging window (IMD-137) | Kirtan, Het; Wed 18 November 2026 |

## Bound, not a value

On the 203-point basis, C ≥ 180 (no cut) holds unless the stories listed above are worth more than 203 − 180 = **23** points. If the listed stories took their card points (IMP-114 3, IMP-402 5, IMP-414 5), they would come to 13. That is shown as context only, because card points are not the rule's basis.

If C were exactly 180, points to cut = max(0, 359 − 360) = 0.

## Decision

**PD-IMP-499-1 (proposed):** no cut at SG-4. All Sprint 1 to 4 stories are complete except those listed above. C ≥ 180 unless the listed stories exceed 23 of the planned 203 points. The supervisor is asked to confirm.

- `FEATURES_DISABLED` and `NEXT_PUBLIC_FEATURES_DISABLED`: unchanged. Only the nine extensions are switched off (IMD-65); no MVP cut-list switch is turned off.
- Task register and `docs/progress`: no card is marked cut.
- Point rebalancing (specification §14.5, "The cut list moves points"): not needed, since nothing is cut.

| Role | Owner |
| --- | --- |
| Gate and checkpoint record | Kirtan (integration lead) |
| Confirmation of PD-IMP-499-1 | Supervisor, with the team |
| If C is later shown to be below 180: re-run steps 4 and 5 and apply cuts by switch in the order above | Kirtan |
