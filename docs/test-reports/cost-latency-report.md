# Cost and latency report (IMP-705)

US-131 AC2; NFR-004, NFR-039, NFR-041. Owner: Nidhi. Date: 19 November 2026; rule-based run added 20 November 2026 (RUN-083b, IMD-213); final GEMINI prompt v2 run (run by the operator) added in RUN-083c. Candidate commit: `f75aa949fe306361d2f515ede632504518d19b63` (`f75aa94`).

Every number in this report comes from a run record under `eval/results/`. The card also allows `ai_generations` rows as a source. None were available: the evaluation harness writes no `ai_generations` rows, the local evaluation database held 0 rows (`select count(*) from ai_generations` returned `(0,)`), and the staging database cannot be reached from this run environment. Anything without a record is marked "not measured".

## Sources

| Run id | Provider · model | Commit | Prompt version (from the record) | Fields used |
| --- | --- | --- | --- | --- |
| [`20261119T182737Z-mock`](../../eval/results/20261119T182737Z-mock/scores.json) | MOCK · `mock-v1` | `f75aa94` | v1 | `latency_ms`, `input_tokens`, `output_tokens`, `error` of 45 attempts |
| [`20261119T182745Z-mock`](../../eval/results/20261119T182745Z-mock/scores.json) | MOCK · `mock-v1` | `f75aa94` | v1 | same |
| [`20261120T155153Z-rule_based`](../../eval/results/20261120T155153Z-rule_based/scores.json) | RULE_BASED · `rule-based` (`rule_based_planner_v1`) | `6993197` (harness change only since `f75aa94`) | not applicable (no prompt) | same |
| [`20261120T165222Z-gemini`](../../eval/results/20261120T165222Z-gemini/scores.json) | GEMINI · `gemini-3.5-flash-lite` | `6993197` (harness change only since `f75aa94`) | v2 (active, IMD-200; overridden with `--prompt-version v2`, IMD-213) | same; 23 attempts with a value |
| [`20261116T042246Z-gemini`](../../eval/results/20261116T042246Z-gemini/scores.json) | GEMINI · `gemini-3.5-flash-lite` | `3a68439` (old ID, before IMD-208) | v3 (not active, IMD-200) | same; earlier run, not the candidate |

`latency_ms` is the provider call's latency as the adapter measures it (`ProviderResult.latency_ms`); for RULE_BASED it is the planner's own run time, measured by the harness around `plan_rule_based`. It is not the end-to-end generation time of NFR-004, which also includes ranking, validation, saving and queueing. The statistics below were computed from the listed `scores.json` files with a short Python calculation: mean, median, and p95 by the nearest-rank method over the attempts that have a value.

## Release candidate (`f75aa94`)

| Measure | MOCK run 1 `20261119T182737Z-mock` | MOCK run 2 `20261119T182745Z-mock` | Rule-based `20261120T155153Z-rule_based` | GEMINI prompt v2 `20261120T165222Z-gemini` (23 completed attempts) |
| --- | --- | --- | --- | --- |
| Attempts | 45 | 45 | 45 | 45 (23 completed, 22 `provider_unavailable`) |
| Provider latency, min / mean / max (ms) | 0 / 0.36 / 1 | 0 / 0.33 / 1 | 0 / 0.76 / 2 (median 1, p95 2) | 1775 / 7471.6 / 19999 (median 6608, p95 12699), over the 23 completed attempts |
| Input tokens per attempt | not measured: the MOCK adapter reports none (null in 45 of 45 attempts) | not measured: null in 45 of 45 attempts | not measured: no model (null in 45 of 45 attempts) | mean 3739.5 (1471 to 4984); 86008 in total; reported in 23 of 23 completed attempts, null in the 22 failed ones |
| Output tokens per attempt | not measured: null in 45 of 45 attempts | not measured: null in 45 of 45 attempts | not measured: no model (null in 45 of 45 attempts) | mean 993.0 (314 to 1957); 22838 in total; reported in 23 of 23 completed attempts |
| Thinking tokens | not measured: the harness does not record them | not measured | not measured: no model | not measured: the harness does not record them |
| Failed attempts | 0 / 45 | 0 / 45 | 0 / 45 | 22 / 45, all `provider_unavailable` (no latency recorded) |
| Fallback rate | not measured: the harness scores the provider's answer alone, without repair or the rule-based fallback (`eval/metrics_v2.md`) | not measured | not applicable: this run is the fallback planner itself | not measured: the harness runs no fallback after a provider failure |
| Cost (USD) | not measured: no dated price table exists (§8.16; numbered metric 12 is null in every record) | not measured | not applicable: no model call | not measured: no dated price table |

MOCK latency only shows that the harness ran without delay. It says nothing about Gemini latency. The rule-based latency shows the planner itself takes at most 2 ms per request on the Mac it ran on; it excludes ranking, validation and saving.

The GEMINI v2 latency and tokens cover only the 23 completed attempts; the 22 `provider_unavailable` attempts (Gemini service errors, not quota) have no value. They are provider-call figures, not the end-to-end generation time of NFR-004.

## Earlier recorded Gemini run (not the release candidate)

Before RUN-083c, the only Gemini run record in the repository with per-attempt latency and tokens was [`20261116T042246Z-gemini`](../../eval/results/20261116T042246Z-gemini/run.json) (RUN-079, 16 November 2026, commit `3a68439`, prompt v3, structured output, thinking level minimal, timeout 35 s). It used a prompt version that is not active and an earlier commit. It is reported here only as a recorded fact, not as the release-candidate figure.

| Measure (44 attempts with a value; 1 attempt failed) | Value |
| --- | --- |
| Provider latency, min / median / mean / p95 / max (ms) | 1649 / 4038.5 / 4878 / 9509 / 20249 |
| Input tokens per attempt, mean (min to max) | 4247 (1588 to 6302); 186868 in total |
| Output tokens per attempt, mean (min to max) | 1356.9 (335 to 4634); 59704 in total |
| Failed attempts | 1 / 45 (`trips-v1-012`, repeat 3, `provider_unavailable`, no latency recorded) |
| Fallback rate | not measured: the harness does not run the fallback |
| Cost (USD) | not measured: no dated price table |

The baseline-1 run [`20261114T104200Z-gemini`](../../eval/results/20261114T104200Z-gemini/run.json) has no committed `scores.json`, so its latency and tokens are not measured in this report.

## Not measured

- GEMINI latency and tokens of the 22 failed attempts of `20261120T165222Z-gemini`: no value recorded.
- GEMINI retrieval timings: no GEMINI retrieval run record.
- End-to-end generation time against NFR-004 (p95 at most 90 s): no staging `ai_generations` rows and no timing of the whole pipeline in any record.
- Fallback rate in the product (`ai_generations.outcome` = `fallback_rule_based`): no `ai_generations` rows available.
- Retrieval time (`ai_generations.retrieval_ms`): the retrieval suite records no timings, and no rows are available.
- Cost in money: no dated price table (§8.16).
- Rule-based planner timing inside the product pipeline (with ranking, validation and saving): not measured; only the planner's own run time is recorded above.
