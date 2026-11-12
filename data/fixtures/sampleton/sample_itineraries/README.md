# Saved sample itineraries (SAMPLE)

Two saved itineraries for the Sampleton SAMPLE destination (§8.15, FR-036 AC3, IMP-402). They are
shown with the "Sample itinerary" label, are built without AI and are never presented as AI output.

| File | Trip case (`eval/datasets/trips/v1/cases.jsonl`) | Days | Transport |
| --- | --- | --- | --- |
| `two_day_walking.json` | `trips-v1-001` (standard) | 2 | walking |
| `five_day_local_transport.json` | `trips-v1-003` (standard) | 5 | local_transport |

## How they were produced

`scripts/build_sample_itineraries.py` runs the rule-based planner (`plan_rule_based`) on each
case's frozen request and stores its io-1 answer unchanged, except that every `place_id` is
replaced by `place_ref: {source_name, external_ref}` taken from `../places.csv` (IMD-145): seeded
place IDs change on every reseed. Places, durations and times all come from the fixture data and
the planner; nothing is written by hand.

```sh
apps/api/.venv/bin/python scripts/build_sample_itineraries.py          # rewrite the files
apps/api/.venv/bin/python scripts/build_sample_itineraries.py --check  # exit 1 if stale
```

`app/generation/samples.py` loads a file by resolving each `place_ref` to the current active
place, then parses io-1, recalculates the times and runs `validate()`. An unknown or inactive
reference fails loudly. `tests/unit/generation/test_samples.py` checks the files are the
planner's current output; `tests/api/test_samples.py` loads them from a seeded database, also after
a reseed.
