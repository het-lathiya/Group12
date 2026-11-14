# Baseline 1 · first Gemini run over trips/v1

- Run id: `20261114T104200Z-gemini` (record: `eval/results/20261114T104200Z-gemini/run.json`)
- Started: 2026-11-14 10:42 UTC, from a clean checkout of `main` at `15475eb` (IMD-176)
- Command: `make eval PROVIDER=GEMINI DATASET=trips/v1`
- Provider and model: GEMINI, `gemini-3.5-flash-lite`; structured output on, thinking level minimal, timeout 35 s
- Prompt: `itinerary_generate` v1 (input and output schema versions as in the record)
- Metrics version: v1 (`eval/metrics_v1.md`)

## Dataset size

15 trips (dataset `trips` v1), 3 repeats each, 45 attempts.

## Metric values

| Metric | Value |
| --- | --- |
| Schema-valid outputs | 44 / 45 |
| Outputs with only valid place IDs | 44 / 45 |
| Usable outputs | 44 / 45 |
| Average daily travel (minutes) | 92.2 |
| Failures | 1: `trips-v1-010`, repeat 2, `schema_violation` |

The numbered metrics 1 to 13 are not computed in metrics v1; the record states the reason for each (blueprint §21.4 not in the repository, no dated price table, or Release 2).

## Observed prompt problems

1. **The model writes the label into the text.** 492 of the 557 item notes start with "AI-written:", as do 38 of the 60 assumptions. The v1 system prompt says the notes "are labelled AI-written", and the model copies that label into the note, so the screen would show the label twice. The prompt should say the application adds the label and the text must not.
2. **Meal places repeat.** 88 items reuse a place already in the same plan: 87 meal slots and 1 activity. Reusing a restaurant can be acceptable, but the prompt does not say whether it is, so the result varies between repeats.
3. **One schema violation in 45 attempts** (`trips-v1-010`, repeat 2). The other two repeats of the same trip were valid, so it is not specific to that trip's input. In the product this path ends in the repair call or the rule-based fallback (§8).
4. Plans held 2 to 7 items a day (average 3.87 over 144 days); no day was empty.

## What this baseline does not claim

This report covers only these 15 trips of dataset v1. It makes no claim about plan quality, accuracy or reliability beyond these 15 trips, for other destinations, for other models or prompt versions, or for live use.
