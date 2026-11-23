# Final report: AI Travel Planner

**Draft — RUN-087, 22 November 2026; human completion pending (Malhar, Manya, Jeel)**

| Item | Value |
| --- | --- |
| Document | Final report of the course project (IMP-804, US-148; NFR-041; CHK-19) |
| Owners | Malhar (lead; data and architecture chapters), Manya (AI chapter), Jeel (presentation, `docs/presentation/`) |
| Version | 0.1, draft of 22 November 2026 |
| Repository state described | `main` at `4fe514c` (the SG-7 release-candidate commit), 22 November 2026 |
| Claims check | [final-report-claims-check.md](final-report-claims-check.md): every numeric claim in this report with the run record, test report, CI run or repository file it comes from (TC-397) |
| Built from | the document set of IMP-707 ([srs.md](srs.md), [architecture.md](architecture.md), [api.md](api.md), [test-plan.md](test-plan.md), [guides/](guides/README.md)), the gate records ([progress/gates.md](progress/gates.md)), [progress/deferred.md](progress/deferred.md), the test reports ([test-reports/](test-reports/README.md)), the evaluation reports ([../eval/reports/](../eval/reports/README.md)), [stage2/](stage2/README.md) and the decision register |

**How to read this draft.** It states only what the repository records. Every number has a row in the claims check; a number without a record was left out. Staging results and every human activity (usability sessions, interviews, device and screen-reader sessions, rehearsal timings) are written as "pending" with an owner; none is reported as done. Where this report and the specification (v1.3 with Amendment A1) differ, the specification wins.

## 1. Summary

The AI Travel Planner is a web application in which a signed-in traveller describes a trip and receives a day-wise, costed and editable itinerary. Gemini proposes the plan from a shortlist of curated places; the backend validates every place ID, recalculates every time, travel gap and price in code, labels every estimate and saves the plan with its warnings. When Gemini fails, a rule-based planner builds a labelled plan. Retrieval-augmented generation (RAG) over curated place records and member-written destination guides is part of the MVP (Amendment A1, IMD-105), so AI-written notes can show their sources.

At the release candidate:

- The SG-6 requirement coverage records every MVP and MVP-S functional requirement as Done, with none cut and none left with a gap ([sprint-6.md](progress/sprint-6.md#requirement-coverage-sg-6-step-1)). The RAG requirements FR-136 to FR-140 have part records for IMP-311 to IMP-318 ([srs.md](srs.md) §4.2).
- The API contract holds the MVP operations only; no extension endpoint is declared or mounted ([api.md](api.md), `contracts/openapi.v1.json`).
- Gates SG-1 to SG-6 passed with listed gaps ([gates.md](progress/gates.md)). SG-7 is recorded as not passed yet (provisional, 22 November 2026, candidate `4fe514c`; [gates.md](progress/gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799)); SG-8 has not been run.
- CI and E2E are green on the candidate commit `4fe514c`: [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091) and [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) (section 6).
- The extensions of the EXT release are cut and not built (IMD-65). Booking, payments and live prices are excluded (IMD-46).
- Staging has not been checked on the candidate commit. The staging journey with Gemini and the other staging criteria are pending (Kirtan, section 10).

## 2. Scope: delivered, cut and not built

### 2.1 Delivered

The MVP release (specification §1.2) with the catalogue item C-13 "Retrieval-augmented Generation with Cited Sources" added by Amendment A1:

- Account sign-up and sign-in (Supabase Auth), profile, dashboard with drafts.
- Trip wizard with preferences, budget and must-visit places; place browsing (Explore).
- AI generation with validation, repair, labelled rule-based fallback and the generation record; progress shown while the job runs.
- Itinerary view with findings, labels and sources; edits (move, add, remove, retime, lock, replace, regenerate a day or the whole plan), each in a single transaction that recalculates and revalidates.
- Costs page with estimate, contingency and budget alerts; summary page with a print view; versions with restore; map with a list fallback.
- RAG: corpus indexing with provenance, semantic retrieval with lexical fallback, cited passages, sources shown next to AI-written notes, and the retrieval evaluation suite.

### 2.2 Cut-list decisions (SG-4 and later)

- **SG-4 checkpoint (IMP-499, 14 November 2026).** The cut-list rule needs the story points of the stories completed before the checkpoint, and the repository holds no per-story point values, so the value could not be computed ([cut-list-checkpoint.md](decisions/cut-list-checkpoint.md)). The team confirmed "no cut-list switch at SG-4" as IMD-167.
- **Later gates.** No MVP cut-list switch was applied at SG-5 or SG-6 (IMD-167, IMD-201). All cut-list features (`versions`, `trip_management`, `contingency`, `budget_alerts`, `wishlist`, `alternatives`, `regeneration`, `locks`, `meal_slots`) are built and on; `FEATURES_DISABLED` defaults to empty ([deferred.md](progress/deferred.md)).
- **Floor journey.** The app still works with every cut-list switch off: the floor journey passed in [E2E 43807026528](https://github.com/het-lathiya/Group12/actions/runs/43807026528) (16 November 2026, `4 passed (34.0s)`) and again in the floor step of [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) on the candidate (`1 passed (14.7s)`).
- **Extensions.** The extensions are cut (IMD-65; IMP-515 and IMP-612 also IMD-186): IMP-515 `ranking_explain`, IMP-612 `optimise_order`, IMP-613 `packing`, IMP-708 `nl_intake`, IMP-709 `day_explain`, IMP-710 `rain_swap`, IMP-711 `today_view`, IMP-712 `budget_fit`, IMP-713 `context_cards`. They have no route, table or screen; the authorization suite checks that none of their routes is mounted (TC-432, [security-sprint7.md](test-reports/security-sprint7.md)).

### 2.3 Excluded and not built

- **Booking, payments and live prices (IMD-46).** No booking provider, payment flow or live price is built, and no screen claims a booking. Prices, hours and travel times are curated or estimated and labelled.
- **T1 release.** Not started and not scheduled: FR-021 nearby places, FR-090 booking checklist, FR-091 weather-aware clothing, FR-097 PDF export (the print view is the MVP substitute), FR-098 read-only sharing, FR-110 booking links, FR-111 place feedback, FR-112 saved and rejected signals ([deferred.md](progress/deferred.md)).
- **R2 release.** Among them FR-006 account deletion by request (API-05); until it is built, deletion is an operator procedure (section 8).
- **PP and Stage 2.** Not built. Stage 2 (fine-tuning, FR-048, FR-049, FR-121, FR-122) is conditional and not done (section 9).

### 2.4 Unfinished MVP work

| Item | State | Owner |
| --- | --- | --- |
| Further demo destination (IMP-603) | Not in the repository; waiting for the members' curated files (IMD-201) | Junaid, Manya, Kirtan |
| Ahmedabad saved sample itineraries (FR-036 AC3) | Waiting for trip inputs | Jeel |
| Itinerary cost strip (IMP-608 step 4) | Not built; the budget alert shows on the Costs page; proposed decision PD-RUN-083-1 records it as a known gap | Krrish, Manal |
| Prompt `itinerary_generate/v3` | Exists, not activated; v2 stays active (IMD-200); see the AI chapter | Manya |
| Usability session (IMP-611), interviews (IMP-114), device and screen-reader check (IMP-703) | Templates merged; sessions not recorded | Junaid, Krrish |

## 3. Data and places

| Data set | Where | What the records show | Source |
| --- | --- | --- | --- |
| SAMPLE destination "Sampleton" | `data/fixtures/sampleton/` | **30** synthetic places and synthetic guides; allowed only in local and test (the seed refuses it elsewhere) | [final-baseline.md](../eval/reports/final-baseline.md) (retrieval database); `data/fixtures/sampleton/guides/` |
| Demo destination Ahmedabad | `data/places/ahmedabad/` | **103** places loaded, meeting the seed's minimum of usable places, with sources, licences and opening hours | [final-baseline.md](../eval/reports/final-baseline.md) (count); [quality report](../data/places/ahmedabad/quality_report.md) (minimum met) |
| Ahmedabad guides (RAG corpus) | `data/guides/ahmedabad/` | Member-written guides, each checked statement by statement against its source by a reviewer (Malhar, 6 November 2026); licences from Creative Commons (CC BY-SA) sources, a U.S. government source and facts-only summaries | [guide quality report](../data/guides/ahmedabad/quality_report.md) |
| Further demo destination | — | Not in the repository (IMP-603 pending) | [deferred.md](progress/deferred.md) |

**Index used for the final evaluation.** Seeded with Sampleton and Ahmedabad and indexed with MOCK embeddings, the RAG index held **151** documents and **227** chunks, all embedded (`rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0`, [final-baseline.md](../eval/reports/final-baseline.md)). The staging index is built by the release task with Gemini embeddings; no staging index line is recorded (pending, Kirtan).

**Data rules that hold in the code.**

- Every price, opening-hours and cost value carries a label (`curated`, `estimate` or `unavailable`); every travel time is `routing_api` or `fallback_estimate`. Curated prices show "Curated" without a date; opening hours keep "checked on <date>" (IMD-130, IMD-149; [label-review.md](test-reports/label-review.md)).
- Place documents in the RAG corpus never carry prices, hours, websites or booking links. Guides pass a strict gate that rejects currency amounts, clock-time ranges and opening-hours phrases ([rag-corpus.md](guides/rag-corpus.md), A1 §6.3).
- Guides of real destinations are written by members. The only generated guides are the synthetic SAMPLE ones (IMP-313).
- No private user data is used for training or evaluation datasets (PD-09); the evaluation datasets are fixed files under `eval/datasets/`.

Open: the IMD-120 data checks (Malhar plan, Junaid sample check, Jeel and Malhar row checks) have no record on `main` (SG-4 and SG-5 open items).

## 4. Architecture and deployment

### 4.1 Application

- **Web:** Next.js App Router with React and TypeScript, Tailwind CSS and shadcn/ui, TanStack Query, react-hook-form with zod, dnd-kit and MapLibre GL with OpenFreeMap tiles. The API client is generated from the OpenAPI contract. The browser displays what the API returns; it never computes prices, totals, times or travel gaps, and only `NEXT_PUBLIC_*` values may reach it ([architecture.md](architecture.md) §4).
- **API:** a modular FastAPI monolith (Python, Pydantic v2, SQLAlchemy 2 async). In every module, routers call services, services call pure domain code and repositories, and clients and adapters sit at the bottom. Each table has a single writing module. The import-linter contracts that enforce these rules report `Contracts: 6 kept, 0 broken.` on the candidate ([CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), job `lint-types`).
- **Generation:** an asynchronous in-process job per request; the browser polls the generation record. The pipeline normalises preferences, retrieves and ranks candidates, builds the request, calls the provider, then parses, checks, recalculates, repairs and saves in a single transaction ([architecture.md](architecture.md) §6). The AI chapter describes the provider layer and RAG.
- **Data:** PostgreSQL 16 with pgvector. The schema is the versioned SQL migrations `0001` to `0007` (`0007_rag_store`): the MVP tables plus `rag_documents` and `rag_chunks` ([srs.md](srs.md) §9 and difference D-02). The extension migrations are retired (IMD-65, IMD-113).
- **Authorization:** the user ID comes only from the verified token; a resource that belongs to someone else answers 404 `NOT_FOUND`. Row-level security is an additional lock ([architecture.md](architecture.md) §5).

### 4.2 Deployment on AWS (as designed and configured in the repository)

The hosting decision is IMD-99 to IMD-104 and Amendment A1 §2 to §5. What the repository configures ([deployment-guide.md](guides/deployment-guide.md), [aws-setup.md](guides/aws-setup.md), `infra/aws/`, `.github/workflows/`):

| Part | Configuration |
| --- | --- |
| Region | AWS `ap-south-1` |
| Web and API | Amazon ECS Express Mode services on AWS Fargate, a service per container in each environment, behind the Application Load Balancer that Express Mode shares; the API health check is `/health` |
| Images | Amazon ECR repositories `group12-api` and `group12-web`, scan on push |
| Secrets | AWS Systems Manager Parameter Store `SecureString` parameters `/group12/<env>/<NAME>`, passed to the API only as ECS `secrets` references; the web image holds no secret (IMD-102) |
| Logs | Amazon CloudWatch log groups per service |
| Database | Amazon RDS for PostgreSQL 16 with pgvector, private, TLS required, holding the auth stub (`DB_AUTH_STUB=true`); databases `travel_staging` and, from IMP-801, `travel_production` (IMD-100, IMD-115) |
| Sign-in | A single hosted Supabase project used for Auth only; the API verifies tokens through JWKS and checks the issuer (IMD-101, IMD-123, IMD-204) |
| CI and deploys | GitHub Actions. `deploy-staging.yml` runs after CI succeeds on `main`; `deploy-production.yml` runs by hand from a release tag with approval in the GitHub environment `production`. Both authenticate through the OIDC role `group12-github-deploy`, so no AWS key is stored (IMD-102) |
| Release task | A one-off ECS task with the new API image before any service changes: auth stub if missing, `alembic upgrade head`, the place seed, then `python -m app.rag.index --strict`; a failure stops the deploy and the running version keeps serving |

Production is not created: `infra/aws/services/` holds only the staging templates (`api.staging.json.tmpl`, `web.staging.json.tmpl`), and IMP-801 creates production. Only Kirtan, the AWS account owner, runs the `infra/aws/` scripts; staging is switched off between staging windows to control cost (IMD-137).

### 4.3 Recorded staging state

- The last **Deploy staging** run is [44733049430](https://github.com/het-lathiya/Group12/actions/runs/44733049430) (20 November 2026, success) for commit `964327f`, not the candidate `4fe514c`. Its release task, service updates and smoke-test step succeeded (`5 passed in 1.66s`). No staging deploy of `4fe514c` is recorded.
- At SG-4 (13 November 2026) the operator recorded a healthy staging `/health` answer with provider GEMINI, but Gemini generations on staging ended `failed` / `config_error` with lexical retrieval ([gates.md](progress/gates.md), SG-4). The SG-5 and SG-6 records keep this open. No later staging generation is recorded on `main`.
- **Staging results on the candidate are pending (Kirtan):** the primary journey with GEMINI, `make smoke`, the timeout fallback demo, the generation cap, edit totals, the staging RAG index line, TC-352, TC-433, TC-434, TC-436, the ECR scan and the NFR-050 timing (section 10).

### 4.4 Differences between documented and built system

The SRS (§11), the architecture document (§11), the deployment guide (§11) and the test plan (§9) list each difference with its source. The main ones: AWS instead of the hosting named in specification v1.3 (IMD-99); extensions not built (IMD-65); the circuit breaker opens after a different failure count than FR-047 states (IMD-146); places unique within a whole generated plan (IMD-181); alternatives ranked lexically (IMD-171); no itinerary cost strip (PD-RUN-083-1); a single demo destination; staging off between windows (IMD-137); no nightly E2E run (IMD-185). Some rows describe `main` at `f75aa94` and were written before the IMP-705 and IMP-706 records existed (SRS D-18); the SG-7 gate is to bring them up to date.

## 5. AI: provider, prompts, retrieval and evaluation

Owner: Manya. This chapter describes the AI path as built on `main` at `4fe514c` and reports only the evaluation figures recorded by IMP-705 ([final-baseline.md](../eval/reports/final-baseline.md), [cost-latency-report.md](test-reports/cost-latency-report.md)). Every figure names its run record under `eval/results/`; each one has a row in the claims check.

### 5.1 What the model does and what code does

The model proposes; code decides. Gemini may choose only place IDs from the shortlist it was given, their order and times, and short notes. Prices, opening hours, travel times, totals and availability always come from data and code. The answer is parsed into `ItineraryOutput` (io-2 under the active prompt v2), every place ID is checked against the shortlist, every time, travel gap and cost is recomputed, the finding codes are applied, and the plan is saved in a single transaction with its warnings and its generation record. Model output never builds SQL, never names a table or user and is never executed (specification §8.1, §8.11).

### 5.2 Provider layer

- **`ModelProvider`** (`apps/api/app/ai/providers/base.py`) is the only way to a model, for generation (`generate_itinerary`) and for embeddings (`embed_texts`). Code outside `app/ai/` imports only the interface, the error classes and the factory; `google-genai` is imported only in `app/ai/providers/gemini.py`, and only `app/ai/factory.py` imports a concrete adapter. The import-linter contracts that hold these rules pass on the candidate ([CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), `Contracts: 6 kept, 0 broken.`).
- **Adapters.** `GEMINI` (model `gemini-3.5-flash-lite`, adapter `gemini-interactions-1`, structured output, thinking level minimal, as recorded in [`20261120T165222Z-gemini/run.json`](../eval/results/20261120T165222Z-gemini/run.json)); `MOCK` (deterministic answers and `mock-embed-v1` embeddings, no network call, the default in local and test, with failure scenarios such as `timeout` and `quota` for tests and demos); `FINETUNED_MODEL`, a Stage 1 stub whose every call is refused and whose selection stops start-up (section 9).
- **Factory.** `AI_PROVIDER` is read at start-up: GEMINI in staging and production, MOCK in local and test. The API refuses to start in staging or production with an empty or placeholder `GEMINI_*` value, and in production with MOCK. There is no per-request override and no automatic switch to another vendor.
- **`RULE_BASED` in the evaluation harness only (IMD-213).** `make eval PROVIDER=RULE_BASED` answers each evaluation request with the production fallback planner (`generation/fallback_planner.plan_rule_based`) and scores it with the same output check, schedule, validator, budget engine and metric code. It builds no provider and is not a product setting; it exists so that the fallback planner can be measured (TC-393).

### 5.3 Errors, retries, repair and the labelled fallback

The shared error taxonomy (specification §8.3, §8.13; [architecture.md](architecture.md) §6 and §9):

| Failure | What the pipeline does | Saved outcome |
| --- | --- | --- |
| Timeout, rate limit, provider unavailable | Retry up to the configured `GEMINI_MAX_RETRIES` inside the time allowance, then the rule-based planner | `completed`, `fallback_rule_based`, with the reason |
| Invalid output (malformed JSON, schema violation, blocked, empty, truncated) or unknown place IDs | Deterministic repair first, then a single bounded model repair call, then the rule-based planner | `model_repaired` or `fallback_rule_based` |
| Plan still not usable after repair | Rule-based planner | `fallback_rule_based`, reason `unresolved_validation` |
| Quota exhausted, key missing or invalid, bad request | No retry and no automatic fallback; the page offers "Build a rule-based plan" | `failed`, `provider_quota_exhausted` or `config_error` |

The circuit breaker opens after a run of consecutive provider failures (IMD-146; `FAILURES_TO_OPEN` in `app/ai/breaker.py`) or after a quota or authorization error; while it is open, the model call is skipped. Every generation writes its `ai_generations` record. The rule-based plan is labelled as built by rules, and the trip's current plan is unchanged until the save step commits.

Evidence in the browser: the provider-failure specs passed on the candidate ([E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127), timeout `1 passed (6.9s)`, quota `1 passed (7.4s)`). The timeout case ends `completed` with outcome `fallback_rule_based`, reason `provider_timeout`, the fallback notice and a saved rule-based plan; the quota case ends `failed` with `provider_quota_exhausted`, no repair call, the paused-AI message and no plan saved until the traveller asks for the rule-based plan ([e2e-sprint7.md](test-reports/e2e-sprint7.md) §2, F-E3). These runs use the MOCK provider. The same demo on staging (IMD-33) is pending (Kirtan).

### 5.4 Prompt versions

| Version | Schemas | What the records show | State |
| --- | --- | --- | --- |
| `itinerary_generate/v1` | gr-1 / io-1 | Baseline-1 with Gemini ([`20261114T104200Z-gemini`](../eval/results/20261114T104200Z-gemini/run.json)): usable outputs 44 / 45, 1 failure (`schema_violation`). [baseline-1.md](../eval/reports/baseline-1.md) found that 492 of the 557 item notes start with "AI-written:" (the screen would show the label twice) and that 88 items reuse a place already in the plan | Kept for comparison; not active |
| `itinerary_generate/v2` | gr-2 / io-2 | Added by IMP-316 for RAG ([model-change-log.md](model-change-log.md)): passages reach the model as quoted reference data, instructions inside them are ignored, a note that relies on a passage cites its ID, prices, hours, travel times and totals are never written; first version with a repair template | **Active** (`PROMPT_TEMPLATE_VERSION=v2` in the application default and the staging template; IMD-200) |
| `itinerary_generate/v3` | gr-2 / io-2 | RUN-079 ([RUN-079-prompt-v3.md](../eval/reports/RUN-079-prompt-v3.md), [`20261116T042246Z-gemini`](../eval/results/20261116T042246Z-gemini/run.json)): Gemini usable 44 / 45 and 0 of 564 notes with "AI-written", but 14 duplicate-place items in 3 attempts, so the IMD-195 activation gate was **not met** | Not active (IMD-200) |

Because v3 is not active, the v1 findings stay recorded as open under v2 (SRS D-14). The validator rejects any repeated place, so a saved plan holds no duplicate, but the plan is shorter. An optional v4 was allowed in Sprint 7 (IMD-200); no v4 exists in the repository.

IMD-213 set the final Gemini evaluation to the active v2. Baseline-1 ran v1, so any comparison between the v1 and v2 runs is **across prompt versions**, not like for like.

### 5.5 Retrieval-augmented generation

RAG is part of the MVP and not on the cut list (IMD-105). It is built only from `google-genai` (through `ModelProvider.embed_texts`) and pgvector in the same PostgreSQL database, with no LangChain, LlamaIndex or separate vector database ([architecture.md](architecture.md) §7).

- **Corpus.** Place documents from active curated places (never prices, hours, websites or booking links) and guide documents from `data/guides/<slug>/`, written by members; the only exception is the synthetic SAMPLE guides used in tests (IMP-313). Guides pass a strict gate that refuses missing provenance, out-of-range length and price, clock-time or opening-hours statements ([rag-corpus.md](guides/rag-corpus.md)). Section 3 gives the data counts.
- **Indexing.** `python -m app.rag.index` chunks the documents, embeds them through `embed_texts` (Gemini embeddings on staging and production, `mock-embed-v1` in local and test) and stores the vectors in `rag_chunks`; removed documents become inactive and are never deleted, so saved citations still resolve. The release task runs it with `--strict` on every deploy.
- **Retrieval.** The trip's query is embedded a single time per generation. Vector queries (exact cosine similarity, same destination and embedding model) live only in `app/rag/repository.py`. Place similarity enters the deterministic hybrid ranking (`pm-2`), and the best guide passages are chosen with maximal marginal relevance.
- **Fallback.** Any embedding error, or no active chunk for the active embedding model, gives `retrieval_mode = lexical_fallback`: the semantic weight becomes zero, no passages are sent and the generation continues. A retrieval failure never fails a generation.
- **Grounding and citations.** Passages are quoted reference data, never instructions and never a source of prices, hours, travel times or totals. An item may cite only a capped number of passage IDs, all of which must have been in its own request (the cap is `MAX_SOURCE_IDS` in `app/schemas/ai.py`, set by A1 §6.10); the output check drops any other ID and counts it. The itinerary page shows each item's sources (title, kind, source, licence, date and a safe link) next to the AI-written note.

### 5.6 Evaluation results (IMP-705, final baseline)

**Conditions** ([final-baseline.md](../eval/reports/final-baseline.md)). Dataset `trips/v1`: 15 cases × 3 repeats = 45 attempts per run, the same dataset hash as baseline-1; metrics v2. The MOCK runs used the candidate commit `f75aa94`; the rule-based and Gemini runs used `6993197`, which differs from it only in the evaluation harness. Each run started from a clean evaluation worktree.

**Generation suite.**

| Measure | MOCK run 1 [`20261119T182737Z-mock`](../eval/results/20261119T182737Z-mock/run.json) | MOCK run 2 [`20261119T182745Z-mock`](../eval/results/20261119T182745Z-mock/run.json) | Rule-based [`20261120T155153Z-rule_based`](../eval/results/20261120T155153Z-rule_based/run.json) | Gemini, prompt v2 [`20261120T165222Z-gemini`](../eval/results/20261120T165222Z-gemini/run.json) |
| --- | --- | --- | --- | --- |
| Attempts completed | 45 / 45 | 45 / 45 | 45 / 45 | **23 / 45** (22 `provider_unavailable`) |
| Schema-valid | 45 / 45 | 45 / 45 | 45 / 45 | 23 / 23 completed (23 / 45 in the record) |
| Only valid place IDs | 45 / 45 | 45 / 45 | 45 / 45 | 23 / 23 completed (23 / 45 in the record) |
| Usable | 45 / 45 | 45 / 45 | 45 / 45 | 23 / 23 completed (23 / 45 in the record) |
| No duplicate places | 45 / 45 | 45 / 45 | 45 / 45 | 19 / 23 completed (19 / 45 in the record) |
| Average daily travel (minutes) | 126.7 | 126.7 | 86.2 | 119.4 (completed attempts only) |

- **Gemini, prompt v2.** Only 23 of the 45 attempts completed; 22 ended `provider_unavailable` (Gemini service errors, not quota), spread through the run. Three cases (`trips-v1-002`, `003`, `012`) have no completed attempt, so 12 of the 15 cases are covered. Over the 23 completed attempts: no invalid place ID, 8 duplicate-place items, all 8 rejected by the output check, and the findings `COST_INCOMPLETE` 7 and `BUDGET_NEAR` 1 ([scores.json](../eval/results/20261120T165222Z-gemini/scores.json)). The record's own counts use all 45 attempts, because a failed attempt counts as not schema-valid. These figures are not a reliability figure for Gemini and say nothing about the three uncovered cases.
- **Rule-based planner.** All 45 attempts schema-valid, with only valid place IDs, usable and without duplicates; `COST_INCOMPLETE` in 15 of 45 attempts (five cases, every repeat), no other finding. It is the fallback planner answering in place of a model through the harness, not the product's fallback rate.
- **MOCK.** Both runs score 45 / 45 on every count; the `metrics` objects of the two records are identical and their raw outputs are identical, so the harness is reproducible (ACC-14). MOCK returns fixed answers, so these runs show that the pipeline runs and scores every case, not model quality.
- **Against baseline-1** ([`20261114T104200Z-gemini`](../eval/results/20261114T104200Z-gemini/run.json): prompt v1, metrics v1, usable 44 / 45, average daily travel 92.2 minutes). The comparison is across prompt versions and across different attempt sets (45 attempts of 15 cases against 23 attempts of 12 cases). Among completed attempts the v2 run had no schema failure, and its average daily travel is 119.4 against 92.2. No conclusion about v2 against v1 is drawn.
- The numbered metrics 1 to 13 are not computed; each record states why.

**Retrieval suite** (`retrieval/v1`, 12 queries, 6 per destination; MOCK embeddings and MOCK answers):

| Metric (overall) | IMP-318 MOCK [`20261113T114756Z-retrieval-mock`](../eval/results/20261113T114756Z-retrieval-mock/run.json) | Final MOCK [`20261119T182831Z-retrieval-mock`](../eval/results/20261119T182831Z-retrieval-mock/run.json) |
| --- | --- | --- |
| recall@6 | 0.7083 | 0.7083 |
| Place hit rate, vector (top 12) | 0.6667 | 0.6667 |
| Place hit rate, lexical (top 12) | 0.7083 | 0.7083 |
| Citation validity | 1.0 | 1.0 |
| Grounding rate | 0.7571 | **0.6392** |
| Citations saved | 68 | 47 |
| Queries in vector mode | 12 of 12 | 12 of 12 |

- In the final run, recall@6 is 0.4167 for Ahmedabad and 1.0 for Sampleton. Citation validity is 1.0, as A1 §6.14 requires.
- **The grounding rate fell from 0.7571 to 0.6392 and the citations saved from 68 to 47 between the IMP-318 and the final MOCK records. This drop is recorded but not investigated.** The records show these differences between the runs: the commit, and the index (the IMP-318 record quotes `embedded=189`, the final run's index printed `embedded=227`).
- MOCK embeddings test the retrieval code path, not semantic retrieval quality.
- **Gemini retrieval was not possible.** The one attempt (20 November 2026, `gemini-embedding-2`) stopped at its first call with `Gemini unavailable: HTTP 503`, wrote no record and was not re-run. No Gemini retrieval figure exists.

### 5.7 Cost and latency

From [cost-latency-report.md](test-reports/cost-latency-report.md), computed from the `scores.json` files of the runs above. The latency is the provider call as the adapter measures it, not the end-to-end generation time of NFR-004.

| Measure | Gemini, prompt v2 [`20261120T165222Z-gemini`](../eval/results/20261120T165222Z-gemini/scores.json) (23 completed attempts) | Rule-based [`20261120T155153Z-rule_based`](../eval/results/20261120T155153Z-rule_based/scores.json) | MOCK [`20261119T182737Z-mock`](../eval/results/20261119T182737Z-mock/scores.json) / [`20261119T182745Z-mock`](../eval/results/20261119T182745Z-mock/scores.json) |
| --- | --- | --- | --- |
| Latency, min / mean / max (ms) | 1775 / 7471.6 / 19999 (median 6608, p95 12699) | 0 / 0.76 / 2 (planner run time only) | 0 / 0.36 / 1 and 0 / 0.33 / 1 |
| Input tokens per attempt | mean 3739.5 (1471 to 4984); 86008 in total | none (no model) | not reported by MOCK |
| Output tokens per attempt | mean 993.0 (314 to 1957); 22838 in total | none | not reported by MOCK |

The MOCK latency only shows that the harness ran without delay. The rule-based figure excludes ranking, validation and saving.

**Not measured:** cost in money (no dated price table exists, §8.16), thinking tokens, the product's fallback rate, end-to-end generation time against NFR-004, retrieval time, Gemini retrieval timings and the latency of the 22 failed Gemini attempts. No `ai_generations` rows from staging were available.

### 5.8 Stage 2 readiness

The Stage 2 readiness package ([stage2/README.md](stage2/README.md), IMP-706, owner Manya) has status **Proposed**. It holds a draft migration gate, a data-governance policy, a dataset schema and a data-card template, and no training code, data, adapter or result. No Stage 2 model has been trained or evaluated. The draft gate compares a candidate with a Gemini run of the same day on `trips/v1` and `retrieval/v1`, and requires a recorded decision and a rehearsed rollback before any provider switch (PD-13). The blueprint criteria E1 to E7 are still "to be confirmed by Manya", and the gate's table of current reference values still shows the final Gemini run as not measured; both are pending (section 10).

### 5.9 What this chapter does not claim

- No claim about plan quality, accuracy or reliability beyond these runs over `trips/v1` and `retrieval/v1`, or for other destinations, models, prompt versions or live use.
- No Gemini retrieval figure, no money cost and no end-to-end timing.
- No staging generation result: Gemini on staging last ended `config_error` (section 4.3), and the staging journey with Gemini is pending (Kirtan).

## 6. Testing and quality

All results below are from CI runs or from the test reports in [docs/test-reports/](test-reports/README.md). The test plan is [test-plan.md](test-plan.md).

### 6.1 CI on the release candidate (`4fe514c`, 22 November 2026)

[CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), push to `main`, success (jobs `audit`, `lint-types`, `unit`, `api`, `guards`; `attribution` runs only on pull requests):

| Suite | Result line |
| --- | --- |
| Unit (`make test-unit`) | `1215 passed, 1 warning in 13.52s` |
| Provider and API contract (`make test-contract`) | `91 passed, 2 deselected, 1 warning in 18.14s` (the deselected tests are the `live` Gemini tests, never run in CI) |
| API and database integration (`make test-api`) | `590 passed, 1 warning in 214.57s (0:03:34)` |
| Authorization (`make test-authz`) | `87 passed, 14 skipped, 1 warning in 44.23s` (the skips are the cut-extension ownership cases, TC-431) |
| Web components (`make test-web`) | `Test Files  43 passed (43)`, `Tests  288 passed (288)` |
| Lint, types, import boundaries | `All checks passed!`; `Success: no issues found in 123 source files`; `Contracts: 6 kept, 0 broken.` |
| Contract files | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| Coverage (report only) | `TOTAL … 92%` for `app`; no threshold fails the build (thresholds still Proposed, test plan T-05) |
| Dependency audit | pip-audit `No known vulnerabilities found`; npm audit `11 moderate severity vulnerabilities`, none critical (critical findings fail the job) |
| Secret scan | gitleaks `445 commits scanned.`, `no leaks found` (history of the pushed branch, IMD-214) |

[E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127), same commit, success (Supabase CLI local stack, Sampleton seed, MOCK provider; the staging job is skipped):

| Step | Result line |
| --- | --- |
| Journey (four widths) | `4 passed (40.8s)` |
| Map specs | `8 passed (20.2s)` |
| Itinerary editing and restore | `8 passed (51.6s)` |
| Regression specs (E2E-01 to E2E-08 at 1280 px, keyboard, extensions) | `12 passed (23.8s)`, `9 skipped` |
| Floor journey, all cut-list switches off | `1 passed (14.7s)` |
| Provider failure, timeout | `1 passed (6.9s)`, `1 skipped` |
| Provider failure, quota exhausted | `1 passed (7.4s)`, `1 skipped` |

### 6.2 E2E regression suite (IMP-701)

[e2e-sprint7.md](test-reports/e2e-sprint7.md): three consecutive local full runs on 18 November 2026 at code head `b6051a8`, retries 0, each `Running 119 tests using 2 workers` and ending `37 skipped`; `82 passed`, with the quota follow-up passing after each run. The **36** extension cases and the quota case account for the skips. The flaky-test list is empty: **0 of 3** full runs failed. The earlier failures (app shell overflow at 360 and 768 px) were deterministic and fixed under IMD-207 before these runs.

### 6.3 Security (IMP-702)

[security-sprint7.md](test-reports/security-sprint7.md), 16 November 2026: unauthenticated requests get 401, another user's resources answer 404, a body `user_id` is refused, SQL and prompt-injection strings are treated as text, logs hold no e-mail, key or notes text, and only `NEXT_PUBLIC_*` values reach the browser bundle. Finding F-1 (a correctly signed token from a foreign issuer was accepted; severity 3) was fixed under IMD-204, and the authorization suite then reported `87 passed, 14 skipped, 1 warning in 62.96s (0:01:02)`. No severity 1 or 2 defect was found. Not verified until a staging window: TC-352 (HTTPS, CORS and observed headers on staging), TC-433 (RDS not reachable from outside), TC-434 (secrets only as SSM references), TC-436 (OIDC trust) and the ECR image scan (Kirtan).

### 6.4 Accessibility (IMP-703)

[accessibility-sprint7.md](test-reports/accessibility-sprint7.md): the automated axe scans found no serious or critical violation in a local run on 20 November 2026 (journey `4 passed (31.6s)` with **40** axe scans; keyboard `4 passed (10.8s)` with **20** scans, every scan `[]`). The real-device and screen-reader sessions (iOS phone, Android phone, desktop screen reader) are an empty template: pending (Junaid runs, Krrish records).

### 6.5 Earlier journey and label evidence

- Sprint 4 journey (TC-369) in CI: [43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989), `4 passed (36.7s)` at four widths ([journey-sprint4.md](test-reports/journey-sprint4.md)). Its staging sections (MOCK and Gemini) are not run.
- Label review ([label-review.md](test-reports/label-review.md)): no displayed value in the reviewed screens lacks its source label; the live-stack review with screenshots (TC-385) is open (Manasvi).

### 6.6 Process

The gate records of SG-3 to SG-6 each hold a working-agreement audit of the merged pull requests ([gates.md](progress/gates.md), "Working-agreement audit"). They record that the working agreement's review-approval requirement was not met at those gates, although the required checks were green on the merged heads.

## 7. Known limitations

- **A single curated destination.** Planning works only for loaded destinations: Ahmedabad, plus Sampleton in local and test. The further demo destination (IMP-603) is not loaded.
- **Staging not checked on the candidate.** The staging journey with Gemini, smoke test, fallback demo and generation cap have no staging record on the candidate; Gemini on staging last ended `config_error` (section 4.3).
- **Production not created** (IMP-801).
- **Estimates, not live data.** Prices, hours and travel times are curated or estimated and labelled; there is no booking, payment or live price (IMD-46). The budget uses the destination currency only (IMD-128).
- **AI limits.** Gemini availability was limited during the final evaluation; the AI chapter states what the records show. Prompt v3 is not active. The model can repeat places; the validator rejects repeated places, which shortens the plan.
- **Performance and usability targets not measured.** NFR-003, NFR-004, NFR-005, NFR-027 and NFR-050 remain Proposed and unmeasured ([srs.md](srs.md) D-17; [cost-latency-report.md](test-reports/cost-latency-report.md) "Not measured").
- **No itinerary cost strip**; totals and budget alerts are on the Costs page (PD-RUN-083-1).
- **No delete-account button**; deletion is an operator procedure (section 8).
- **Human evidence missing.** The usability session, discovery interviews and the device and screen-reader check have no recorded results.
- **Coverage is reported but not enforced** (test plan T-05).
- **User guide differences.** The guide lists where the built app differs from the specification's screens, for example no link to the trip edit page and the itinerary totals shown on Costs ([user-guide.md](guides/user-guide.md) §12).

## 8. Manual account-deletion procedure (NFR-022)

There is no delete-account screen in the MVP; FR-006 (API-05) belongs to the R2 release. The procedure is documented in [deployment-guide.md](guides/deployment-guide.md) §9, from Amendment A1 §5.1 and IMD-101, and summarised in [srs.md](srs.md) §9.9 and [user-guide.md](guides/user-guide.md) §11. Kirtan carries it out on a traveller's request:

1. **Supabase Auth.** In the Supabase dashboard (Authentication, Users), find the user, note the user ID (a UUID) and delete the user.
2. **The database row.** Run a one-off ECS task with the API task definition and the command `python -m app.db.admin delete-user --user-id <uuid>`. It deletes the user's `auth.users` row in a single transaction; the foreign keys cascade to the profile, trips and plans. The command refuses unless `DB_AUTH_STUB` is true and prints only `delete-user: N row(s) deleted`. The e-mail address is never stored in the database.
3. **Record** the date and the request, never the e-mail address.

State of the evidence: the command's database behaviour is covered by the IMP-219 tests on the compose database ([IMP-219 part record](progress/parts/IMP-219-whole-task.md)); its `--help` output was checked while writing the deployment guide. The one-off task on RDS and the Supabase dashboard step have **not** been run or recorded (pending, Kirtan).

## 9. Stage 2 position

Stage 2 (fine-tuning a model behind the `FINETUNED_MODEL` adapter) is **conditional and not done**. It is not part of the course commitment, its go or no-go is decided by the team with the supervisor after the MVP (OD-13), and nothing in the planned sprints depends on it ([stage2/README.md](stage2/README.md)).

- The `FINETUNED_MODEL` adapter is a stub that refuses every call; selecting it stops start-up. `AI_PROVIDER` stays GEMINI in staging and production and MOCK in local and test.
- The readiness package of IMP-706 (status **Proposed**, owner Manya) holds a draft migration gate, a data-governance policy, a dataset schema and a data-card template. It contains no training code, data, adapter or result, and no Stage 2 model has been trained or evaluated.
- The blueprint criteria E1 to E7 that the gate must map are not in the repository and are marked "to be confirmed by Manya" ([migration-gate-criteria.md](stage2/migration-gate-criteria.md)).
- A switch of provider needs the gate, a recorded decision and a rehearsed rollback (PD-13); an environment variable change alone is not enough.

## 10. Pending items

Due 26 November 2026 unless a record gives another date. Dates of earlier records that have passed are noted.

| Item | Owner | Due |
| --- | --- | --- |
| Staging deploy of the candidate `4fe514c` and a green `/health` reporting it | Kirtan | 26 Nov 2026 |
| Staging results on the candidate: primary journey with GEMINI (regenerate a day, restore a version, summary), `make smoke`, timeout fallback demo (IMD-33), generation cap 429, edit totals, staging RAG index line, Gemini `config_error` resolved, NFR-050 timing, CORS, TC-438 | Kirtan, Het (Gemini key) | 26 Nov 2026 (record date 18 Nov 2026 passed) |
| TC-352, TC-433, TC-434, TC-436 and the ECR image scan on staging | Kirtan | 26 Nov 2026 (record date 18 Nov 2026 passed) |
| Account deletion: run the procedure on staging (Supabase step and one-off ECS task) and record the result | Kirtan | 26 Nov 2026 |
| Monthly AWS cost estimate in [aws-setup.md](guides/aws-setup.md) §14 ("TO BE FILLED BY KIRTAN") | Kirtan | 26 Nov 2026 |
| Production environment and deploy (IMP-801) | Kirtan | as set by IMP-801 |
| Device and screen-reader sessions (IMP-703) | Junaid, Krrish | 26 Nov 2026 |
| Usability session (IMP-611) and discovery interviews (IMP-114, PR #201) | Junaid, Krrish | 26 Nov 2026 (record dates 18 and 19 Nov 2026 passed) |
| Further demo destination (IMP-603): load it, or record it as deferred under IMD-201 | Junaid, Manya, Kirtan | 26 Nov 2026 (record date 19 Nov 2026 passed) |
| Ahmedabad saved sample itineraries (FR-036 AC3) | Jeel | 26 Nov 2026 (no date in the record) |
| IMD-120 data checks recorded | Malhar, Junaid, Jeel | 26 Nov 2026 (no date in the record) |
| Deployment-guide trial by a member outside the platform squad, and user-guide trial by a new member (IMP-707 step 6) | Kirtan to arrange | 26 Nov 2026 |
| Decision on PD-RUN-083-1 (itinerary cost strip) | Krrish, Manal, team | 26 Nov 2026 |
| Stage 2: confirm E1 to E7 against the blueprint; update the "Current reference values" in [migration-gate-criteria.md](stage2/migration-gate-criteria.md), which still say the final Gemini run was not measured although `20261120T165222Z-gemini` now exists | Manya | 26 Nov 2026 |
| AI chapter of this report (section 5) | Manya | 26 Nov 2026 |
| Presentation in `docs/presentation/`, rehearsed to fit the slot, stating that Stage 2 is conditional and not done | Jeel | 26 Nov 2026 |
| Complete and review this report; bring the SRS and architecture difference lists up to date at SG-7 | Malhar | 26 Nov 2026 |
| Manual review of the claims check (TC-397) | Junaid | 26 Nov 2026 |
| SG-7 gate (IMP-799) | Kirtan | 26 Nov 2026 |

## 11. Any-city mode (Amendment A2)

**Status: built behind a switch; the switch state at the release is to be recorded at the cutoff** (27 November 2026 23:59 IST, IMD-215). If the batches are not green with the switch both OFF and ON by then, the release ships with the switch OFF, and this chapter describes the work as built but disabled.

- **What it is.** A signed-in traveller can type any city. The API resolves it with Nominatim, imports places from the Overpass API, labels every value as live, and stores the places through the places module. Wikivoyage and Wikipedia sections are indexed as guide passages with their CC BY-SA attribution. The normal trip, generation, itinerary and costs screens then work for that city (IMD-210; Amendment A2).
- **What did not change.** The model still chooses only stored place IDs. Prices, hours, travel times and totals still come from data and code, and live places carry no price and no hours. The curated destination and the SAMPLE fixture behave as before, whatever the switch. With the switch OFF, the any-city routes answer 404 and the city search is absent.
- **Decisions.**
  - IMD-210: scope.
  - IMD-215: the feature-freeze exception and the cutoff.
  - IMD-216: the switch token `!any_city_mode`, a separate any-city contract, the User-Agent, no live opening hours, every country supported.
  - IMD-217: a failed refresh keeps a working city active; the global daily cap stays.
  - IMD-218: a guide-source failure keeps the import, without guides.
- **Built in Sprint 7, batches C1 to C3 (RUN-089 to RUN-092).** Migration 0008. The live-data providers with throttling and breakers. The normaliser and the minimum-places gate. The import job, reaper and CLI. API-76 to API-79. The live guide corpus with corpus caps. Prompt template v4 (not active; v2 stays). The web city search, import progress, tier badge, source badges, unknown chips and attribution footer. The E2E `@live` journey. The switch-ON CI jobs. The authorization and injection tests. The live evaluation dataset.
- **Cut (A2 §1.3).** Lexical guide passages when embeddings are missing: live plans without embeddings cite no guide passage, as IMD-112 does today.
- **Evidence.**
  - The live evaluation dataset `trips/live-v1` gave usable plans in 24/24 MOCK attempts and 24/24 rule-based attempts. Every planned live place had an unknown price ([live-v1-2026-11-23.md](../eval/reports/live-v1-2026-11-23.md)).
  - The full existing API suite passed with the switch OFF and with it ON ([any-city-switch.md](test-reports/any-city-switch.md), TC-490). With the switch ON, two inventory or start-up-configuration authz tests failed beyond the four that A2 §3.4 names; the record explains both, and PD-730-1 proposes adding them to §3.4.
  - The security addendum found no defect ([security-any-city.md](test-reports/security-any-city.md)).
- **Pending.** The staging pre-import of the demo cities (PD-AC-2, proposed) and ACC-20 to ACC-23 on staging, both in Kirtan's window of 28 November 2026 ([any-city.md](acceptance/any-city.md), [any-city-staging.md](guides/any-city-staging.md)). Reading the live-data services' usage policies (Junaid). One GEMINI evaluation run for template v4 (IMD-195), in the operator's later window.
