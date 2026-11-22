# Presentation outline: AI Travel Planner

**Draft — RUN-087, 22 November 2026; human completion pending (Jeel)**

**Slot length and rehearsal timing: pending (Jeel)**

| Item | Value |
| --- | --- |
| Card | IMP-804, part "Presentation slides" (US-148 AC2; NFR-041; TC-397) |
| Owner | Jeel |
| State described | `main` at `4fe514c` (the SG-7 release-candidate commit), 22 November 2026 |
| Sources | [final-report.md](../final-report.md) only, including its section 5 (AI chapter). No figure in this outline comes from anywhere else |
| Claims check | Every number below has a row in [final-report-claims-check.md](../final-report-claims-check.md), section "Presentation outline (docs/presentation/outline.md)", rows O1 onwards, each naming the report section and the claims-check row it comes from |
| Slides file | Not made yet: pending (Jeel). This file is the outline only |

**Rules for completing the slides.** Use only the figures written here, all of which appear in the final report, and keep each figure with its qualifier (for example "completed attempts only", "MOCK embeddings", "provider call only"). The strict source rule of RUN-087 applies to the slides as to the report: a number appears only if the report states it with a run record, test report or CI run behind it. Do not add participant feedback, demo results, timings or staging results that have no record; write "pending" with the owner instead. If a figure changes in the report, change it here and in the claims check in the same change.

Every slide has the target slot time "to be measured in rehearsal (Jeel)". No timing has been measured.

---

## Slide 1 — Title

**On the slide**

- AI Travel Planner: Stage 1 (MVP) result
- A signed-in traveller describes a trip and gets a day-wise, costed, editable itinerary
- Course project; state shown: `main` at `4fe514c`, 22 November 2026
- Presenters: pending (Jeel)

**Speaker notes.** Introduce the product in a sentence and say what the talk covers: what was built, how the AI is kept in check, what the tests and the evaluation show, what is still open, and the Stage 2 position. Say early that the figures come from recorded CI runs, test reports and evaluation records, and that anything not recorded is called pending.

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 2 — Problem

**On the slide**

- Planning a trip means combining places, opening hours, travel times and costs into days that actually work
- A language model on its own can name places, prices or hours that are not real
- Our approach: Gemini proposes a plan from a shortlist of curated places; code checks and recalculates every value
- Out of scope by decision: booking, payments and live prices (IMD-46)

**Speaker notes.** The design rule is "the model proposes; code decides" (report section 5.1). The model may only choose place IDs from the shortlist it was given, their order and times, and short notes. Prices, opening hours, travel times, totals and availability always come from data and code, and every estimate carries a label. Say plainly that the app does not book anything.

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 3 — Users

**On the slide**

- Traveller (signed in): creates trips, sets preferences and must-visit places, generates, edits and versions itineraries, sees labelled costs and sources
- Visitor: landing page, sign-up and sign-in only
- Team roles in the system: curator (places and guides with provenance), evaluator (evaluation harness), operator (deploys and the account-deletion procedure)
- No administrator UI

**Speaker notes.** User classes are from the SRS ([srs.md](../srs.md) §2.2). Do not quote user feedback: the discovery interviews (IMP-114) and the usability session (IMP-611) have templates but no recorded results, so their findings are pending (Junaid, Krrish). If the slot allows, say that the user research is incomplete and will be added when recorded.

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 4 — Features shipped

**On the slide**

- Every MVP and MVP-S functional requirement recorded as Done at SG-6, none cut and none with a gap
- Trip wizard; AI generation with validation, repair and a labelled rule-based fallback; itinerary edits that recalculate and revalidate; costs, versions, summary and map
- Retrieval-augmented generation: AI-written notes show the guide passages they rely on
- All cut-list features built and on, and the app still works with every cut-list switch off (floor journey `1 passed (14.7s)` on the candidate)
- Data: Ahmedabad with 103 curated places and member-written guides; final evaluation index of 151 documents and 227 chunks

**Speaker notes.** Requirement coverage is from the SG-6 record (report section 1). The floor journey passed on the candidate in E2E 45037634127 (report sections 2.2 and 6.1). The extensions of the EXT release are cut and not built (IMD-65): they have no route, table or screen, and the API contract holds the MVP operations only. Ahmedabad's places meet the seed's minimum of usable places, and each guide was checked statement by statement against its source (report section 3). The index figures are from the final evaluation with MOCK embeddings; no staging index line is recorded (pending, Kirtan).

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 5 — Demo flow (pointer)

**On the slide**

- Journey: sign in, create a trip, generate, read the itinerary with warnings, costs and sources, edit, restore a version, open the summary
- Step-by-step reference: [user guide](../guides/user-guide.md), sections 2 to 10
- Demo script and backup video: IMP-801, pending (Kirtan, Nidhi)
- Ahmedabad saved sample itineraries (FR-036 AC3): pending (Jeel)

**Speaker notes.** There is no `docs/demo/` folder yet; the demo script, rehearsal log and backup video belong to IMP-801 (Kirtan lead, Nidhi for the script and video). Until then the user guide is the reference for the journey; its section 12 lists where the built app differs from the specification's screens. No demo result is reported here. The journey has been recorded only with the MOCK provider in CI (slide 8); the staging journey with Gemini is pending (Kirtan). Do not show a live result as evidence unless it is recorded.

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 6 — Architecture

**On the slide**

- Next.js web app (displays only what the API returns) → FastAPI modular monolith → PostgreSQL 16 with pgvector
- Layer rules (routers → services → domain and repositories → adapters) enforced by import-linter: `Contracts: 6 kept, 0 broken.`
- Schema: versioned SQL migrations `0001` to `0007`: the MVP tables plus `rag_documents` and `rag_chunks`
- AWS `ap-south-1` as configured in the repository: ECS Express Mode on Fargate, ECR, SSM Parameter Store, CloudWatch, RDS; GitHub Actions deploys through an OIDC role
- Production not created yet (IMP-801); staging last deployed for `964327f`, not the candidate

**Speaker notes.** Suggested visual: boxes for the browser, the API and the database, with Supabase Auth for sign-in only and Gemini and OpenRouteService reached only by the API (report section 4.1). The user ID comes only from the verified token, and another user's resource answers 404; row-level security is an additional lock. Secrets reach the API only as SSM references and no AWS key is stored. Say clearly that the AWS table describes what the repository configures; the staging state on the candidate is pending (Kirtan, report section 4.3).

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 7 — AI and evaluation

**On the slide**

- Model proposes, code decides: invalid output or unknown place IDs get deterministic repair, a single bounded model repair call, then a labelled rule-based plan; cited passage IDs are capped and must come from the item's own request
- Final baseline on `trips/v1`: 15 cases × 3 repeats = 45 attempts per run
- Gemini, prompt v2: 23 of 45 attempts completed (22 `provider_unavailable`); all 23 completed attempts usable; 8 duplicate-place items, all rejected by the output check
- Rule-based planner 45 / 45 usable; MOCK runs 45 / 45 and identical, so the harness is reproducible
- Retrieval (MOCK embeddings): citation validity 1.0; grounding rate fell from 0.7571 to 0.6392, recorded but not investigated; Gemini retrieval not possible (HTTP 503)

**Speaker notes.** All figures are from report sections 5.3 to 5.7 and the run records named there. Qualify every Gemini figure: only 12 of the 15 cases have a completed attempt, so the figures are not a reliability figure for Gemini and say nothing about the three uncovered cases. The rule-based run measures the fallback planner through the harness, not the product's fallback rate. MOCK returns fixed answers, so the MOCK runs show that the pipeline runs and scores every case, not model quality; MOCK embeddings test the retrieval code path, not semantic quality. Gemini provider-call latency over the 23 completed attempts: mean 7471.6 ms (median 6608, p95 12699); this is the provider call only, not end-to-end generation time. Not measured: cost in money, end-to-end generation time, retrieval time. Prompt v3 is not active because its duplicate-place result did not meet the activation gate (slide 9).

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 8 — Testing

**On the slide**

- CI on the candidate `4fe514c`: unit 1215 passed, provider and API contract 91 passed, API and database 590 passed, authorization 87 passed (14 skipped), web components 288 passed
- E2E on the candidate (MOCK provider): journey at four widths `4 passed (40.8s)`; floor journey, provider-failure timeout and quota specs passed
- Regression suite: three consecutive local full runs of 119 tests, 0 of 3 failed
- Security: finding F-1 (severity 3) fixed; no severity 1 or 2 defect. Accessibility: 40 + 20 automated axe scans, no serious or critical violation
- Coverage 92% for `app`, reported but not enforced

**Speaker notes.** CI and E2E runs: [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091) and [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) (report section 6.1). The authorization skips are the cut-extension ownership cases; the deselected contract tests are the live Gemini tests, never run in CI. Secret scan: `no leaks found` over `445 commits scanned.`. The device and screen-reader sessions and the staging security checks (TC-352, TC-433, TC-434, TC-436, ECR scan) are pending (Junaid, Krrish; Kirtan). Process: the working-agreement audits of SG-3 to SG-6 record that the review-approval requirement was not met at those gates, although the required checks were green (report section 6.6).

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 9 — Limitations

**On the slide**

- Ahmedabad is the only curated destination loaded; the further demo destination (IMP-603) is not in the repository
- Staging not checked on the candidate; Gemini on staging last ended `config_error`; production not created
- Performance and usability targets (NFR-003, NFR-004, NFR-005, NFR-027, NFR-050) not measured; no cost in money
- Prompt v3 not active (14 duplicate-place items in 3 attempts); the model can repeat places, and the validator's rejection shortens the plan
- No itinerary cost strip; no delete-account button (operator procedure); usability, interview and device results not recorded

**Speaker notes.** From report sections 2.4, 4.3, 5.4 and 7. Prices, hours and travel times are curated or estimated and labelled; there is no booking, payment or live price, and the budget uses the destination currency only. Account deletion is a documented operator procedure (report section 8) that has not yet been run on staging (pending, Kirtan). The open items and their owners are in report section 10, due 26 November 2026.

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 10 — Stage 2: conditional and not done

**On the slide**

- Stage 2 (fine-tuning a model behind the `FINETUNED_MODEL` adapter) is conditional and not done
- Not part of the course commitment; nothing in the planned sprints depends on it; go or no-go is decided by the team with the supervisor after the MVP (OD-13)
- `FINETUNED_MODEL` is a stub that refuses every call; selecting it stops start-up
- Readiness package (IMP-706) is Proposed: draft gate, data-governance policy, dataset schema and data-card template; no training code, data or result, and no model trained or evaluated
- Any provider switch needs the gate, a recorded decision and a rehearsed rollback (PD-13)

**Speaker notes.** From report sections 5.8 and 9. Say this slide without hedging: there is no Stage 2 result to show. The blueprint criteria E1 to E7 that the gate must map are still "to be confirmed by Manya", and the gate's reference values still show the final Gemini run as not measured; these are pending (Manya). No private user data is used for training or evaluation datasets (PD-09).

**Target slot time:** to be measured in rehearsal (Jeel)

---

## Slide 11 — Team and contributions

**On the slide**

- Backend: Manal, Het (main); Junaid (helper, and testing)
- Database: Malhar, Jeel
- AI/ML: Nidhi, Manya
- Frontend: Manasvi (main); Krrish (helper, and testing)
- Deployment and DevOps: Kirtan (also integration lead and gate owner)

**Speaker notes.** Roles are the member areas of the Team Contribution Plan (specification Appendix C, the source of [TASK_REGISTER.md](../spec/TASK_REGISTER.md)). Each card names its lead and parts; each merged part has a record in [progress/parts/](../progress/parts/README.md) and every commit is authored by the part's owner. The final report was written by Malhar (data and architecture chapters) and Manya (AI chapter); the presentation is Jeel's part. Do not add point totals or per-member figures to this slide unless the final report states them.

**Target slot time:** to be measured in rehearsal (Jeel)
