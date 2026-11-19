# Stage 2 data-governance policy (draft)

- Status: Proposed
- Owner: Manya (Manya Rana)
- Date: 19 November 2026
- Card: IMP-706 step 2 (US-132); FR-122 (Stage 2: keep training data separate and governed); NFR-023

The card bases this policy on blueprint §18.8. The blueprint is not in the repository. Where the policy depends on it, it says "to be confirmed against blueprint §18.8 by Manya".

## 1. Rules already decided

| Rule | Source |
| --- | --- |
| Runtime, user, training and evaluation data are separate. `eval/` and `data/` are separate from user tables, and no user data goes into datasets | PD-08 |
| No private user data is used for training without consent and governance. Default: excluded | PD-09 |
| No training on private data by default: 0 user-derived records in any training export | NFR-023 (TC-361) |
| Model output (Gemini or any other assistant's) is excluded as Stage 2 training data until a recorded terms review permits it | OD-17 (owner: Nidhi with the supervisor, before Stage 2) |
| The evaluation set is separate from any training data: no evaluation case appears in a training set | FR-118 AC2 (TC-284) |
| Generation records never store prompt text, the raw model response, notes, e-mail or name | §8.16 |
| Generation records and logs are kept 90 days (`retention_until`) and purged daily | OD-10, IMD-31 |
| Interview and usability notes use participant codes only | IMD-185 |

This policy adds to these rules and changes none of them.

## 2. Private user data and consent

- The MVP has no consent process for training. Therefore **no private user data is used for training**. This covers trips, preferences and notes, itineraries, saved places, versions, `ai_generations` rows, logs, and interview and usability notes.
- A consent process would be a new decision. It would need its own privacy-notice wording (the current wording is fixed by IMD-125), opt-in, withdrawal and deletion. What such a process must contain is to be confirmed against blueprint §18.8 by Manya.
- Until such a decision is recorded, any record derived from a user is refused, even when anonymised.

## 3. Allowed sources and licences (Proposed)

| Source | Allowed for training examples | Licence rule |
| --- | --- | --- |
| Examples written by members for Stage 2, in their own words | yes | The author and date are recorded in each example (`source.author`) |
| Curated place records in `data/places/<slug>/` | facts only (place IDs, categories, tags, durations, hours, prices as structured input) | The `licence` of the record's `data_sources` row is copied into the example. For "All rights reserved (facts only)" sources, no text is copied |
| Team-written destination guides in `data/guides/<slug>/` | yes, as reference passages | Licence `Team-written summary` (A1 §6.3) |
| SAMPLE fixtures in `data/fixtures/sampleton/` | yes, labelled SAMPLE | Licence `synthetic test data` |
| Evaluation datasets in `eval/datasets/` | **no** | FR-118 AC2 |
| Gemini or other model output | **no**, unless OD-17 is resolved by a recorded terms review | OD-17 |
| Any user table, `ai_generations`, logs | **no** | PD-09, NFR-023 |

Every example names its source and licence in the fields of [dataset-schema.md](dataset-schema.md). An example whose source or licence is unknown is refused.

## 4. Storage and retention (Proposed)

- No training store is created in the MVP (§4.1), and no training data is committed to this repository.
- Where a Stage 2 dataset would be stored, who may read it, and how long it is kept are to be confirmed against blueprint §18.8 by Manya.
- Proposed default until then: the dataset is kept only while Stage 2 is active. The data card states its deletion date, and deletion is recorded in the data card's change log.

## 5. Approval (Proposed)

| Step | Approver | Basis |
| --- | --- | --- |
| Terms review for using model output | Nidhi with the supervisor | OD-17 |
| Approval of a dataset version (data card complete, checks of section 6 passed) | Manya (data governance), with the supervisor; to be confirmed against blueprint §18.8 by Manya | This policy |
| Stage 2 go or no-go | The team with the supervisor | OD-13, PD-13 |

## 6. Checks before any dataset is used (Proposed)

1. The data card ([data-card-template.md](data-card-template.md)) is complete and approved.
2. Every example validates against the schema of [dataset-schema.md](dataset-schema.md).
3. Overlap check: no example's input equals or is derived from a case of `eval/datasets/` (FR-118 AC2).
4. User-data check: 0 user-derived records (NFR-023). This is the property TC-361 states for code paths: no code path exports user data to training files.
5. Every source has a licence that allows the use (section 3).
