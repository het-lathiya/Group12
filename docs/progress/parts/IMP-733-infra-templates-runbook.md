# IMP-733 · infra-templates-runbook part (A2 §7.2 template values and the import task)

- Card: IMP-733 (0 points, Amendment A2 §12); follow-up of the any-city readiness audit
- Part: PD-733-G1 (built), PD-733-G13 (built), PD-733-G5 (**not built**)
- Run id: RUN-096 (batch H, Sprint 7 close)
- Owner: Kirtan (chaudhari kirtan sandipbhai)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: A2 §3.2, §7.2, §7.3; IMD-102, IMD-215, IMD-220; TC-462, TC-491

## What was built

- **G1.** The eleven A2 §7.2 values are in `api.staging.json.tmpl`: `LIVE_DATA_PROVIDER=LIVE`, the defaults of `deployment.md` section 10, and `WIKI_USER_AGENT` as a placeholder (no real value). They are constants, so the set of `${…}` names and the deploy workflow's `check_template` are unchanged.
- **G13.** The exact one-off task for the import CLI is in `any-city-staging.md`, on the pattern of the account-deletion task, marked "Not verified — run by Kirtan". The runbook also names `--force` and the embedding re-run of this batch, and PD-AC-2 as adopted (IMD-220).

## Not built

- **G5, the production template: needs its values.** The proposal ("create the production templates, or record the production values another way") defines none, and no `PRODUCTION_*` value is in the repository. It stays open for IMP-801.
- **A `${STAGING_WIKI_USER_AGENT}` variable: needs a workflow change** (`deploy-staging.yml` would have to export it, else `check_template` stops the deploy). So the contact goes into the template itself.

## Changed files

- `infra/aws/services/api.staging.json.tmpl`
- `docs/guides/any-city-staging.md`
- `docs/progress/parts/IMP-733-infra-templates-runbook.md` (this record)

Nothing was applied to AWS.

## Commands

| Command | Result line |
| --- | --- |
| script: the `${…}` names of the template before and after | `placeholders unchanged True 9` |
| script: the template parses as JSON after substitution | 33 environment entries, all eleven names present |
| script: the template's environment through `Settings` and `check_settings` | switch OFF: starts; ON with the placeholder: `WIKI_USER_AGENT is empty or a placeholder (needed with LIVE)`; ON with a value: starts |

The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **A2 §7.2 values in the staging template, placeholders only: verified** (scripts above).
- **The import task command: written, not verified** (needs AWS; Kirtan).
- **No workflow change: verified** by the diff.

## Proposed decisions

none

## Open issues

- With the switch ON and the placeholder still in the template, the API refuses to start, so the deploy fails. Kirtan must replace it first (PD-733-G2). The template is in the repository, so the contact should be a team address.
- The template value of the contact is visible to everyone who can read the repository; keeping it out needs the workflow change above.

## Blockers

none for this part
