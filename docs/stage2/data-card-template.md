# Stage 2 data-card template (draft)

- Status: Proposed
- Owner: Manya (Manya Rana)
- Date: 19 November 2026
- Card: IMP-706 step 3 (US-132)

Copy this template for each version of a Stage 2 training dataset, fill every field, and have it approved under [data-governance-policy.md](data-governance-policy.md) §5 before the dataset is used. A field that cannot be filled is written "unknown" with the reason. Such a field blocks approval until it is resolved. Every number on a card must come from a recorded check or run (NFR-041). This template holds no data and no results.

---

## Data card: `<dataset_id>` `<dataset_version>`

### 1. Identity

| Field | Value |
| --- | --- |
| Dataset id and version | `<dataset_id>` / `<dataset_version>` |
| Status | Draft / Approved / Withdrawn |
| Owner | `<member>` |
| Date of this card | `<YYYY-MM-DD>` |
| Example schema | [dataset-schema.md](dataset-schema.md), schemas `gr-1` / `io-1` (or `gr-2` / `io-2`, per that document's open point) |

### 2. Purpose

- What the dataset is for: `<one sentence>`
- What it must not be used for: evaluation (FR-118 AC2), and any use outside Stage 2.

### 3. Composition

| Field | Value (from a recorded count) |
| --- | --- |
| Number of examples | `<n>` |
| Destinations | `<slug: count, ...>` |
| Examples by `source.kind` | `member_written: <n>`, `curated_derived: <n>`, `synthetic_sample: <n>` |
| Trip lengths, paces and scopes covered | `<summary>` |
| Command or script that produced these counts | `<command and its output line>` |

### 4. Sources and licences

| Source | Licence | Attribution text | Used for | Examples |
| --- | --- | --- | --- | --- |
| `<data_sources name or "member-written">` | `<licence>` | `<text or none>` | `<facts / passages / whole example>` | `<n>` |

### 5. Collection and review

- How the examples were written or derived: `<procedure>`
- Authors: `<members>`
- Reviewers and review result: `<members, accepted / rejected counts>`

### 6. Privacy and consent

| Check | Result | How checked |
| --- | --- | --- |
| User-derived records | must be 0 (NFR-023, PD-09) | `<check and output line>` |
| `user_data` is `false` in every example | `<yes / no>` | `<schema validation output line>` |
| Model output used | must be none while OD-17 is open | `<check>` |
| Personal data (names, e-mails, contacts) in any text field | must be none | `<check>` |

### 7. Separation from evaluation

| Check | Result | How checked |
| --- | --- | --- |
| Inputs equal to or derived from a case of `eval/datasets/trips/<version>` | must be 0 (FR-118 AC2) | `<check and output line>` |
| Queries equal to or derived from `eval/datasets/retrieval/<version>` | must be 0 | `<check and output line>` |
| Evaluation dataset hashes compared against | `<dataset_sha256 values>` | from the evaluation manifests |

### 8. Validation

| Check | Result | How checked |
| --- | --- | --- |
| Every example validates against the schema of dataset-schema.md | `<k / n>` | `<command and output line>` |
| Every output passes the rules of dataset-schema.md (shortlist IDs, no repeats, days and limits, no blocking finding) | `<k / n>` | `<command and output line>` |

### 9. Known limitations

- `<for example: destinations covered, trip lengths not covered, language>`

### 10. Storage, retention and deletion

| Field | Value |
| --- | --- |
| Where stored (never in this repository, §4.1) | `<location>`; to be confirmed against blueprint §18.8 by Manya |
| Who may read it | `<members>` |
| Deletion date | `<YYYY-MM-DD>` |

### 11. Approval

| Step | Name | Date | Decision |
| --- | --- | --- | --- |
| Terms review for model output (OD-17), if relevant | `<name>` | `<date>` | `<permitted / not permitted>` |
| Dataset approval (data-governance-policy §5) | `<name>` | `<date>` | `<approved / refused>` |

### 12. Change log

| Date | Version | Change | By |
| --- | --- | --- | --- |
| `<YYYY-MM-DD>` | `<version>` | `<change>` | `<member>` |
