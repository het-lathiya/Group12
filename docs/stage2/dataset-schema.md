# Stage 2 dataset schema (draft)

- Status: Proposed
- Owner: Manya (Manya Rana)
- Date: 19 November 2026
- Card: IMP-706 step 3 (US-132)

One training example is one generation request and the itinerary a good answer would be. The input is the gr-1 request the backend sends to the model (`contracts/ai/gr-1.schema.json`, `$id` `urn:ai-travel-planner:schema:gr-1`). The output is the io-1 answer the backend accepts (`contracts/ai/io-1.schema.json`, `$id` `urn:ai-travel-planner:schema:io-1`). The other fields record where the example came from, as [data-governance-policy.md](data-governance-policy.md) requires. No example exists yet. This document defines the shape only and adds no export code.

## Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `example_id` | string (UUID) | Stable identifier of the example |
| `dataset_id`, `dataset_version` | string | The training dataset and its version, as named in its data card |
| `input` | gr-1 `GenerationRequest` | The request: trip context, preferences (with `notes_quoted`), must-visit IDs, shortlist, day hints, limits, locked items, scope, repair context, prompt template and version |
| `output` | io-1 `ItineraryOutput` | The answer: days with theme and items (`place_id`, `start_time`, `duration_min`, `slot_type`, `note`), optional summary, assumptions |
| `source.kind` | enum | `member_written`, `curated_derived` or `synthetic_sample` (data-governance-policy §3) |
| `source.author` | string | The member who wrote or derived the example |
| `source.licences` | array of string | The licence of every data source the example uses |
| `source.created_on` | date | `YYYY-MM-DD` |
| `user_data` | const `false` | Every example must hold this value. No user-derived record is allowed (PD-09, NFR-023) |
| `model_output_used` | const `false` | Model output is excluded while OD-17 is open |
| `review.reviewer`, `review.status`, `review.date` | string, enum, date | A second member's review of the example |

## JSON Schema fragment (Proposed)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:ai-travel-planner:schema:stage2-training-example-draft",
  "title": "Stage2TrainingExample (Proposed)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "example_id", "dataset_id", "dataset_version", "input", "output",
    "source", "user_data", "model_output_used", "review"
  ],
  "properties": {
    "example_id": { "type": "string", "format": "uuid" },
    "dataset_id": { "type": "string", "minLength": 1 },
    "dataset_version": { "type": "string", "minLength": 1 },
    "input": { "$ref": "urn:ai-travel-planner:schema:gr-1" },
    "output": { "$ref": "urn:ai-travel-planner:schema:io-1" },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "author", "licences", "created_on"],
      "properties": {
        "kind": { "enum": ["member_written", "curated_derived", "synthetic_sample"] },
        "author": { "type": "string", "minLength": 1 },
        "licences": { "type": "array", "items": { "type": "string", "minLength": 1 }, "minItems": 1 },
        "created_on": { "type": "string", "format": "date" }
      }
    },
    "user_data": { "const": false },
    "model_output_used": { "const": false },
    "review": {
      "type": "object",
      "additionalProperties": false,
      "required": ["reviewer", "status", "date"],
      "properties": {
        "reviewer": { "type": "string", "minLength": 1 },
        "status": { "enum": ["pending", "accepted", "rejected"] },
        "date": { "type": "string", "format": "date" }
      }
    }
  }
}
```

## Rules a JSON Schema cannot express (Proposed)

1. Every `output.days[].items[].place_id` is a `place_id` of `input.shortlist`, and every place appears at most once (§8.11, IMD-181).
2. Every `output.days[].day_number` lies between 1 and `input.trip.num_days`, and each day respects `input.limits` (§8.11, §8.12).
3. The output passes the production validator with no blocking finding (`UNKNOWN_PLACE`, `OUTSIDE_TRIP_DATES`, `OVERLAP`, `CLOSED_ON_DAY`), as the evaluation harness checks it.
4. The output carries no price, opening hour, travel time or total. io-1 has no such field, and notes must not state them (PD-14).
5. `input.preferences.notes_quoted` is written by a member, never copied from a user.
6. The `input` equals no case of `eval/datasets/` and is not derived from one (FR-118 AC2).

## Open point

The card asks for gr-1 and io-1. The active prompt v2 (IMD-200) uses gr-2 and io-2 (`contracts/ai/gr-2.schema.json`, `io-2.schema.json`), which add retrieved passages and citations. Whether Stage 2 examples use gr-1 / io-1 or gr-2 / io-2 is to be decided before any example is written. The fields above stay the same; only the two `$ref`s change.
