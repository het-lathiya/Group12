# A2 · provider-policy-facts part (external facts from the provider usage policies)

- Document: Amendment A2 §16 and the any-city readiness audit §3 and §7 (documents only, 0 points)
- Run id: RUN-096 (batch H), addendum, Part 12
- Owner: Het (Het Lathiya; author of Amendment A2)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: PD-733-G2, PD-733-G3; A2 §7.2, §7.3, §16; IMP-723 step 8

## Changed files

- `docs/spec/AMENDMENT_A2_ANY_CITY.md`: §16 only, three rows added after the Nominatim, Overpass and MediaWiki rows; the earlier rows and the OpenStreetMap row are unchanged. The prompt allows this edit for this part only.
- `docs/test-reports/any-city-readiness.md`: §3 (a table of the facts) and §7 (rows G2 and G3).
- `docs/progress/parts/A2-provider-policy-facts.md` (this record)

## Source of the facts

The facts and their URLs were supplied by the planner in the run prompt, with the status "checked by the planner on 25 Nov 2026 against the source; confirmation by Junaid (IMP-723 step 8) pending". This run opened none of the pages and made no live call. Nothing states that Junaid checked anything.

## Wording kept exact

- "Stay within 100 queries per day" is written as "at most 100 queries per day for new imports": the cap counts new imports only. Re-queued failed imports (audit G20) and CLI imports are outside it, and the guidance's data volume (under 1 GB, divided by 100) is not bounded by it. The audit says so.

## Commands

Documents only. The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **Each fact with its URL and the given status: verified** by reading.
- **Nothing else in A2 changed: verified** (`git diff`: §16 rows only).
- **The facts themselves: not verified in this run** — pending (Junaid).

## Proposed decisions

none

## Open issues

- The IMP-723 record (23 November) still says the Nominatim page could not be read; Junaid updates it on confirmation.
- "Matches A2 §7.3" holds while one API task runs (IMD-12): the throttle is per process.

## Blockers

none
