# RAG corpus: writing and checking destination guides

For curators. A guide is a short Markdown file that gives the planner background on a destination: how people get around, local customs, food culture. Its passages reach the model as quoted reference data, and travellers can see where a note came from. The full rules are in `docs/spec/AMENDMENT_A1_AWS_RAG.md` §6.2 to §6.6.

## Where files go

- Curated destinations: `data/guides/<destination slug>/<name>.md`, one topic per file.
- Suggested topics: getting around, neighbourhoods and areas, local customs and etiquette, safety and health, accessibility, food culture, seasonal and weather notes, day-trip context.
- `quality_report.md` in the same folder is not read as a guide.
- `data/fixtures/sampleton/guides/` holds three synthetic SAMPLE guides for tests. It never reaches a deployed image.

## File format

Each file starts with flat `key: value` lines between two `---` lines. Nested YAML is not allowed.

```text
---
title: Getting around Example City
source_name: Wikivoyage
source_type: other
url: https://en.wikivoyage.org/wiki/Example_City
licence: CC BY-SA 4.0
attribution_text: Adapted from the Wikivoyage article on Example City, CC BY-SA 4.0.
retrieved_on: 2026-11-01
curated_by: Your Name
---

## Walking

Your text, in your own words.
```

| Field | Rule |
| --- | --- |
| `title` | Required, 1 to 120 characters |
| `source_name` | Required, 1 to 120 characters; pages of one source use the same name |
| `source_type` | Required: `official_site`, `curated_manual` or `other` |
| `url` | Required unless `source_type` is `curated_manual`; `https://` only; the page you used |
| `licence` | Required: the source's licence, or `Team-written summary` |
| `attribution_text` | Required when the licence is a CC BY licence |
| `retrieved_on` | Required, `YYYY-MM-DD`, not in the future |
| `curated_by` | Required, a team member's name |

The body uses `##` section headings and is 300 to 6,000 characters long.

## What to write

- Write in your own words from the cited source. A short quote is allowed, and Wikivoyage text may be adapted under CC BY-SA with attribution.
- English. Facts only: no invented places or events.
- No prices, opening hours, travel times, live information or booking claims. Those facts come from `places`, the budget engine and the routing service.

## What the gate checks

Errors always keep a guide out of the index:

- a missing or invalid field, a `url` that is not `https`, a body outside the length limits;
- a `source_name` that already exists with a different licence or attribution text (several pages of one source may have different URLs);
- SAMPLE text outside `APP_ENV` local or test.

These content patterns are warnings, and errors with `--strict`, which is what the release task uses:

- a currency amount, such as a currency symbol or code next to a number, or `Rs`, `INR`, `USD`, `EUR` with digits;
- a clock-time range such as `10:00 to 17:00`;
- the phrases "open daily", "opening hours", "closed on" and "minutes by".

Each finding names the file, the line and the rule. Fix strict findings before you open a pull request, because an error fails the release.

## Commands

Run these from the repository root, on a migrated and seeded database.

| Purpose | Command |
| --- | --- |
| Check one destination, writing nothing | `make rag-index ARGS='--destination <slug> --check --strict'` |
| Index one destination | `make rag-index ARGS='--destination <slug>'` |
| Index everything | `make rag-index` |

The report gives documents, chunks, chunks embedded in this run, inactive documents, warnings and errors. It never prints guide text.

| Exit code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Guide-gate errors with `--strict`; nothing was written |
| 2 | Usage error, such as an unknown destination |
| 3 | Embedding provider unavailable; saved batches stay, and a re-run resumes |

A second run with no change embeds nothing. A changed paragraph re-embeds only the chunks that changed. A deleted guide is set inactive and its rows stay, so saved citations keep resolving.
