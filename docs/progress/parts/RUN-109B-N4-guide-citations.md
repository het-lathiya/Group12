# RUN-109B N4 — guide citation trace

Owner: Manya Rana. 0 points. Base: `0346ee8`. Related: IMP-316, IMP-318, IMP-726;
FR-138, FR-139, FR-140; TC-454 to TC-456. Status: regression coverage verified;
the cause of the original live N4 observation remains unconfirmed (PD-RUN-109B-1).

The current code does **not** reproduce a guide citation being lost. The active v2 template
uses gr-2/io-2, not io-1. `request_builder.ground` places guide chunk UUIDs (with null
place_id) in context_passages before place chunks. v2 explicitly tells the provider to put
passage_id in source_ids when a note relies on it. Gemini selects io-2 from that template's
metadata. io-1 has no citation field and is unchanged. The output check accepts all supplied
passage UUIDs, independently of the shortlist. Recalculation, deterministic repair, the
save mapper and API-24 preserve those validated IDs and resolve both guide and place sources.
Live document keys and curated document keys are never citation IDs: both use chunk UUIDs.
Prompt size control can remove passages before the call; the existing generation record
counts passages sent/dropped, but the original live run did not record their kinds or outputs.

The default MOCK adapter deliberately cites only place passages (`_cited`), so its previous
success could not establish that guide sources reach API-24. A scripted MOCK response now
quotes a supplied guide in a note and returns its UUID alongside a duplicate and a foreign
document key. New database/API regressions cover both curated Sampleton and a fully imported
live Liveton, using **v2** and vector retrieval. They assert the rendered prompt includes the
UUID, the output cites it, the saved item and snapshot retain it, and API-24 returns its guide
SourceRef, including live attribution. Invalid citations are removed without losing the note.

PD-RUN-109B-1: the RUN-107 report alone cannot distinguish a provider choosing not to use a
guide from guide passages not reaching that particular request. No raw response is available
in the repository or local database. No production fix is claimed. Inspect a recorded response
and passage counts by kind in a later authorized live run before changing retrieval or prompting.
Published v2/v3 and inactive v4 remain unchanged (IMD-200); no contract change is needed to
carry guide citations. Do not attach unused sources merely to increase the grounding rate.

Validation:

- `pytest tests/api/test_itinerary.py tests/api/test_live_generation.py -k n4 -q`:
  `2 passed, 30 deselected in 6.72s` (before formatting-only assertion splits).
- `pytest tests/api/test_itinerary.py tests/api/test_live_generation.py -q`:
  `32 passed in 53.93s` (final assertions).
- `pytest tests/unit/rag tests/unit/ai tests/unit/generation tests/unit/validation tests/contract -m 'not live' -q`:
  `968 passed, 2 deselected, 1 warning in 40.23s`.
- `ruff check .`: `All checks passed!`; `ruff format --check .`: `283 files already formatted`.
- `mypy app`: `Success: no issues found in 140 source files`.
- `make imports`: `Contracts: 8 kept, 0 broken.`
- `make openapi-check`: `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date`.

MOCK evaluation (v2, three repeats for the generation suites; metadata and metrics in
`eval/reports/RUN-109B-N4-mock.json`):

```text
trips/v1: schema/place IDs/usable 45/45; citation validity N/A (0 citations); grounding rate 0.0000 (0/507 notes).
trips/live-v1: schema/place IDs/usable 24/24; citation validity N/A (0 citations); grounding rate 0.0000 (0/219 notes).
retrieval/v1: 12/12 vector queries; citation validity 1.0000 (47 citations); grounding rate 0.6392 (mean per query).
```

Commands: `make eval PROVIDER=MOCK DATASET=trips/v1 ARGS='--prompt-version v2'`, the same
for `trips/live-v1`, and `make eval PROVIDER=MOCK DATASET=retrieval/v1 ARGS='--suite retrieval'`.
The frozen trip datasets contain no passages; their N/A validity and zero grounding are expected,
not evidence of a live regression. The retrieval suite used a separate local PostgreSQL test
database, seeded with SAMPLE Sampleton and curated Ahmedabad and indexed with mock-embed-v1
(227 chunks embedded, 0 queued). No real provider was called; RUN-109A files were untouched.
