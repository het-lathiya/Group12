# Build the IT314 draft submission

Run from a clone containing all merged course sources:

```sh
make submission-zip
make submission-zip SUBMISSION_REF=<commit-or-ref>
```

The default is `HEAD`; the ref resolves once to an immutable commit. Output is `dist/12.zip`,
with a complete `dist/12.files.txt` manifest and `dist/12.summary.json` provenance/size report.
`dist/` is ignored. No ZIP is committed, no branch is changed, and untracked/unstaged files are
not imported into the source archive. For the final hand-in, rerun against the agreed merged ref.

The tools run via uvx/npx caches: python-pptx 1.0.2, pypdf 7.2.0, Mermaid CLI 12.2.0 and
marked 18.3.0, plus an installed Chromium browser. No repository dependency manifest/lockfile is
modified. Set `PUPPETEER_EXECUTABLE_PATH` if needed. `make lint` can use externally installed tools.

## Payload

- Course items 01, 03–09, 11–13 and 15 each get a PDF, made from the ref's Markdown.
- Item 02 has one PDF per sprint. Mermaid diagrams are rendered with mmdc before HTML is printed.
- Item 14 has the editable PPTX and a printable PDF built from the same slide content.
- **10 Source code → source/ (git archive of the selected ref, commit recorded in INDEX).**
  Item 10 deliberately has no PDF, per the RUN-102 clarification.
- `docs/spec/` contains the specification set; `test-reports/course/` contains the raw course reports.
- `INDEX.txt` maps every payload file to a course item/purpose and records the selected ref/commit.
- `LINKS.txt` leaves the live URL, YouTube link and repository URL as `[team to fill]`.
- `BUILD.json` records source exclusions and optional coverage HTML provenance. Ratings, signatures,
  a timed rehearsal and release/live evidence remain the team's work; this is a draft package.

Missing numbered documents, duplicate items, an incomplete sprint set, missing images or rendering
failures stop the build. Course sources must already be in the selected ref; the builder does not
silently read another branch/worktree or manufacture pending PDFs.

## Coverage HTML

If HTML reports exist at `apps/api/course-coverage/html` or `apps/web/course-coverage/report`,
they are included. Explicit downloaded artifacts may be supplied instead:

```sh
make submission-zip ARGS='--coverage-api-dir <api-html-dir> --coverage-web-dir <web-report-dir> --coverage-run-url <Actions-run-URL>'
```

The HTML inputs must contain `index.html`. Their historic measured commit/run is distinct from the
submission's source ref; the course summaries and BUILD provenance retain that distinction.

## Inspection and exclusions

The source archive excludes environment files (including example templates), key-file paths,
sensitive-path names and generated directories (`node_modules`, `.venv`, `mutants`, `dist`).
Symlinks are refused. The specification is copied separately from the filtered snapshot.

The staged payload is checked for forbidden paths and the requested provider/access-key prefixes;
only file names are reported on failure, never a matched value. PDF text and PPTX XML are inspected,
then ZIP integrity and member paths are checked before the output atomically replaces an older ZIP.

Four non-code historical reports contain literal scanner-prefix examples in their audit commands.
They are omitted from the source archive, never rewritten, and listed in INDEX/BUILD:

- `docs/progress/parts/IMP-514-gemini-baseline.md`
- `docs/progress/parts/IMP-705-whole-task.md`
- `docs/progress/parts/IMP-732-gemini-v4-result.md`
- `eval/reports/final-baseline.md`

Their originals remain at the selected git ref. Product source, evaluation datasets and runtime
logic are retained. Other unexpected prefix matches still fail the staged-payload scan.

For an inspection-only negative/positive fixture check, use
`bash scripts/build_submission_zip.sh --check-only <staged-directory>`.

Local full `make check` and E2E: not run — operator fast mode; CI covers.
