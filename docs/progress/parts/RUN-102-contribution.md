# RUN-102 · IMD-221 · contribution document

Owner: Nidhi (`Nidhi Chauhan`). Base and contribution snapshot:
`57b620901ff610900ce46c004a27bcae68cc695e` (updated main before PR).

Created the unsigned per-member contribution Markdown/PDF, a frozen evidence JSON, a standard-library
collector/rebuilder and a shared Chromium PDF renderer. The ten member roles and ownership rows come
from the task register/specification; planned totals come from A1 §10.5, not the superseded Appendix C.
Merged allocations sum Sprint 1–7 ledger rows plus the separately recorded IMP-399 and IMP-499 gates.
They explicitly do not award acceptance credit or marks. Pending human/staging outcomes stay pending.

`git shortlog -sne origin/main` was read at the initial snapshot and refreshed against the
pinned integration-main SHA because another session can advance the shared remote-tracking ref.
The final totals include merged batch-B work and exclude this branch. PRs containing owned work are separated
from the operator's PR authorship. The actual merged-PR review query is frozen, not guessed.

Commands and actual result lines:

- `python3 scripts/build_contribution.py --refresh --ref 57b620901ff610900ce46c004a27bcae68cc695e --prs <downloaded merged-PR JSON>`:
  `Contribution draft: 10 members; plan=403; merged allocations=368; main commits=512; submitted reviews=1`.
- `gh pr list --state merged --limit 1000 --json number,title,author,reviews,url,mergedAt,headRefName`:
  98 merged PR records downloaded; one APPROVED review by `kirtan-S111` on PR #2. No offline activity inferred.
- `PUPPETEER_SKIP_DOWNLOAD=true npx --yes --package=@mermaid-js/mermaid-cli@12.2.0 --package=marked@18.3.0 -c 'node scripts/render_course_pdf.mjs docs/course/15-contribution.md docs/course/15-contribution.pdf'`:
  `PDF exported: /home/hetlathiya/Group12-run102/docs/course/15-contribution.pdf`.
- External pypdf reload/text checks: `15-contribution.pdf : 20 pages; text extraction OK`;
  `Contribution PDF: ten members, unsigned marks placeholder, frozen counts verified`.
- Shared slide HTML/PDF print smoke: `slides-preview.pdf : 10 pages; text extraction OK`.
- Ruff check: `All checks passed!`; Node syntax check and Prettier applied to the renderer.
- Local-link validation: `Contribution local links: PASS`.

Acceptance: role/card/part allocation, merged-versus-plan accounting, main commits, PR references,
recorded reviews and course ownership documented per member. The marks line remains
`[team to decide; default equal]`; all ten member signatures plus the leader confirmation are blank.
The printable PDF preserves those placeholders. No signature, review, rating or earned human credit invented.

Final `make lint` and packaging checks are recorded by the submission part. Local full
`make check`/E2E: not run — operator fast mode; CI covers.
No protected files, contracts, migrations or repository dependency manifests changed.
