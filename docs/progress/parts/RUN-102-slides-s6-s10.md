# RUN-102 · IMP-804 draft · slides S6–S10

Owner: Manya (`Manya Rana`). Base: `bc2b606e504ba167c3c5fad9d992c7500dc9fb44`.

Extended the shared presentation script/content/deck to the exact course order, including sourced
lessons, measured testing achievements, historic mistakes and unfilled ratings. Added the rebuild,
source and human-completion guide. Speaker notes distinguish local mutation results, CI coverage,
proposed speaking time and historic gate evidence. No survey, retrospective feedback or rating is invented.

Sources: batch-A documents, gate/security records, and PR #302's raw reports read by `git show` at
`b40b00a54011a5d2120341cd2d2d5569c4b6d0d9`; the parallel branch and its worktree are untouched.

Commands:

- `uvx --from python-pptx==1.0.2 python docs/course/14-slides/build_slides.py --reuse-diagram`:
  `PPTX reload: 10 slides; titles in order; speaker notes present`;
  `Target slot: 300 seconds planned; rehearsal not run`.
- Ruff formatter/check on the script: `All checks passed!`.
- Full build, print/export and final `make lint` verification are recorded by the submission part.

Acceptance: ten slides reload in the required order; S6–S8 notes cite actual records; S9 and S10
retain `[team to fill]`. The team still supplies ratings, signatures, a presenter and timed rehearsal;
Junaid's TC-397 human review remains pending. No earned points claimed for this draft.
Local full `make check`/E2E: not run — operator fast mode; CI covers.
No contracts, migrations, dependency manifests or protected files changed.
