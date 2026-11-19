# IMP-707 · user-guide part

- Run id: RUN-083 (docs-guides batch)
- Owner: Jeel
- Status: PARTIAL (document drafted; screenshots and the new-member trial of card step 6 are open)
- Base commit: f75aa94
- Branch: S7B/docs-guides (batch branch of RUN-083; the card names `feat/IMP-707-<part>`, and the lead integrates the batch)
- Issue: #157

## Changed files

- docs/guides/user-guide.md (created)
- docs/progress/parts/IMP-707-user-guide.md (created)

## What was done

Card step 3: the user guide covers account creation, the trip wizard, generation (privacy notice, progress, rule-based fallback, daily limit), reading the itinerary, every edit control (time, remove, add, move, drag, lock, replace, regenerate), costs, the labels Estimate, Curated, Unavailable, Traveller input and AI-written, the other trip pages, and known limits including "curated destinations only". It was drafted from the code at f75aa94 (`apps/web/app`, `apps/web/components`, `apps/web/lib`, and the API rules in `apps/api/app/generation/service.py`, `apps/api/app/trips/service.py`, `apps/api/app/places/import_pipeline.py`), from `infra/aws/services/api.staging.json.tmpl` for the staging limits, and from specification §7.8 and §7.9. Every screen text quoted in the guide was copied from the source files. Screenshots are placeholders "Screenshot to be added by Jeel: <screen>" (16 placeholders). No image was generated.

The guide contains no shell command, so card step 5 ("run every command it documents") has nothing to run for this part.

## Commands run

All run in this worktree at base f75aa94 with no product change, with `PYTHONPATH=/home/user/wt-S7B-docs-guides/apps/api` and the proxy variables unset.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make help` | exit 0 (prints the target list, first line `Targets (specification §4.7):`) |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make lint` | `All checks passed!`; `234 files already formatted`; `All matched files use Prettier code style!` (eslint printed no finding) |
| `make typecheck` | `Success: no issues found in 123 source files`; `✓ Types generated successfully` (tsc printed no error) |
| `make imports` | `Contracts: 6 kept, 0 broken.` |

## Not run

| Command | Reason |
| --- | --- |
| Walking through the guide in a running app (`make stack-up`, `make api`, `make web`) | The run rules forbid the Supabase stack, Docker and databases (other runs use them). The guide is checked against the source code only |
| `make e2e` | Needs the local stack; not allowed in this run. Existing evidence for the journeys is in docs/test-reports/e2e-sprint7.md (not re-run here) |
| Screenshots | Taken by the team (card step 3); not generated |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Each required document exists in docs/ with owner and version (US-145 AC1), for the user guide | verified | docs/guides/user-guide.md has the header table with Owner Jeel and Version 0.1 |
| A new member created a trip and an itinerary from the user guide without help (US-146 AC1) | not verified | Card step 6 is a team trial; it has not happened. Its outcome goes into docs/progress/sprint-7.md |
| make openapi-check is green | verified | `make openapi-check` result line above |
| Card step 5: every difference between documented and built behaviour is listed | verified (from the code) | Section 12 of the guide lists six differences; none was checked in a running app |

## Differences between documented and built behaviour (guide section 12)

1. `/trips/<id>/edit` exists but no screen links to it; saved trip details "cannot be changed here" in the normal wizard.
2. The out-of-date banner's **Regenerate** opens the generate page, where the API refuses a new generation for a trip that already has a plan ("This trip already has an itinerary. Regenerate it instead."); **Regenerate all** on the itinerary page is the working path.
3. Specification §7.8 SampleBanner "SAMPLE data, not a real destination" is not on the itinerary page; the SAMPLE hint is on the wizard's destination field and Explore.
4. The §7.9 wireframe shows the estimated total and budget percentage in the itinerary header and day tabs on desktop; the built header has neither (totals are on Costs; day tabs only below 768 px).
5. §7.9 puts two panes from 1024 px; the built page uses 1280 px (`xl`).
6. The item card shows the hours label without "checked on <date>"; the dated form appears only in the Explore place details.

## Blockers

- Screenshots and the new-member trial (card step 6) need team members and a running deployment.

## Proposed decisions

- none. Differences 1 and 2 may deserve a defect card after the feature freeze review (IMD-201); this record only reports them.

## Open issues

- When the second demo destination (IMP-603) is loaded, section 11 "Curated destinations only" needs its name.
- If staging's `FEATURES_DISABLED` switches features off, the guide's sections 7 and 10 describe controls the traveller will not see; section 11 says so in general terms.
