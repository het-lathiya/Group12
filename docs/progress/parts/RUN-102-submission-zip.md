# RUN-102 · IMD-221 · submission ZIP builder

Owner: Kirtan (`chaudhari kirtan sandipbhai`). Status: implementation verified; draft hand-in.
Integration base: `57b620901ff610900ce46c004a27bcae68cc695e`.

The isolated branch began at `bc2b606e504ba167c3c5fad9d992c7500dc9fb44`. After PR #302
merged, only this branch was updated onto the integration base above. The parallel branches
and their worktrees were not changed. The contribution snapshot is pinned to that base.

Changed files: `scripts/build_submission_zip.sh`, `scripts/build_submission_zip.py`,
`Makefile`, `.gitignore`, `docs/guides/course-submission.md` and this record. The tools run in
external uvx/npx caches; no repository dependencies or lockfiles were changed.

The builder resolves one ref (default `HEAD`) once and exports its tracked source with
`git archive`. It renders Mermaid before printing the numbered Markdown documents, renders
one PDF per sprint, rebuilds the editable slide deck and its printable view, includes the
specification and course test reports, and optionally imports downloaded coverage HTML with
its run URL. `INDEX.txt` maps every payload file; `LINKS.txt` retains the requested placeholders.
Item 10 is **Source code → source/**, per the RUN-102 clarification, with ref and commit in
the index. No item-10 PDF or pending substitute is produced.

## Commands and actual results

- `make submission-zip ARGS='--coverage-api-dir /tmp/run-099-evidence.jRTXN3/coverage-final-46126005122/coverage-api/html --coverage-web-dir /tmp/run-099-evidence.jRTXN3/coverage-final-46126005122/coverage-web/report --coverage-run-url https://github.com/het-lathiya/Group12/actions/runs/46126005122'`
  at pre-builder-commit `HEAD=0edcf366d807fc973372f1a532dad2a02e94807b`:
  `Submission result: files=1553 course_pdfs=21 source_files=1070 bytes=14617787`;
  `ZIP integrity: PASS; forbidden paths: none; key-prefix scan: PASS`.
- Python ZIP inventory/integrity assertions:
  `Archive validation: PASS; 21 course PDFs; 8 sprint PDFs; source-only item 10; integrity PASS`.
  The manifest contains `source/` (1070 files), `docs/spec/` (32), raw course reports (6),
  API coverage HTML (147) and web coverage HTML (273). These are observed payload counts,
  not test totals. The final committed-ref package and size are reported in the PR/SYNC.
- The packaged slide rebuild:
  `PPTX reload: 10 slides; titles in order; speaker notes present`;
  `Target slot: 300 seconds planned; rehearsal not run`.
- `make lint` (exit 0, external Ruff/ESLint/Next/Prettier tools):
  `All checks passed!`; `271 files already formatted`;
  `All matched files use Prettier code style!`.
- `uvx --from ruff==0.17.3 ruff check --select E4,E7,E9,F,I,B docs/course/14-slides/build_slides.py scripts/build_contribution.py scripts/build_submission_zip.py`:
  `All checks passed!`.
- Ruff format check with line length 100: `3 files already formatted`.
  `node --check scripts/render_course_pdf.mjs` and `bash -n scripts/build_submission_zip.sh`
  exited 0; Prettier check: `All matched files use Prettier code style!`.
- External temporary negative/positive safety probes, run with the builder's actual inspection
  functions: `Safety probes: PASS (forbidden paths and all requested key prefixes rejected; ordinary task text accepted)`.

Coverage HTML was downloaded from [Course reports 46126005122](https://github.com/het-lathiya/Group12/actions/runs/46126005122),
measured on its historical CI commit; it does not measure the submission ref. The included
raw summaries retain their measured commands, counts and links.

## Acceptance and limits

- Verified: numbered PDFs, separate sprint PDFs, PPTX, test evidence, specification, source,
  per-file index, link placeholders, ignored output and ZIP integrity.
- Verified: forbidden path filtering, refusal of symlinks, staged text/PDF/PPTX inspection,
  negative key-prefix probes and atomic output replacement. No matching value is printed.
- Four non-code historical reports contain literal scanner-prefix examples. They are omitted
  from the source archive and listed in INDEX/BUILD rather than rewritten:
  `docs/progress/parts/IMP-514-gemini-baseline.md`,
  `docs/progress/parts/IMP-705-whole-task.md`,
  `docs/progress/parts/IMP-732-gemini-v4-result.md`, `eval/reports/final-baseline.md`.
  All other staged prefix matches still fail the build. Their originals remain in git.
- Not verified: final human ratings, marks distribution, signatures, TC-397 review, timed
  rehearsal, release/staging evidence and final live/video links. These remain team tasks.
- Local full `make check` and E2E: **not run — operator fast mode; CI covers**.

No contract, migration, required check, protected course/index/spec file or dependency manifest
changed. Blockers: none for this draft. Proposed decisions: none.
