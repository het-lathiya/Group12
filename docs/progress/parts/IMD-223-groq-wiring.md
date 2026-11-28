# IMD-223 · Groq staging and production settings

- Run: RUN-108 · Owner: chaudhari kirtan sandipbhai (Kirtan) · Points: 0
- Status: wiring implemented for the combined `feat/groq-provider` pull request; account actions pending
- Base commit: `8e7dd4fb6471cf3e7108e2d3e7410b448e4c78ca`
- Traces: IMD-223, IMD-102, PD-RUN-103-1; FR-043, NFR-013, NFR-037

## Changes

- `.github/workflows/deploy-staging.yml`, `deploy-production.yml`: read optional repository variables
  `STAGING_GROQ_MODEL_ID`, `PRODUCTION_GROQ_MODEL_ID`. The existing envsubst renderer fills plain
  API environment. Both update helpers remove the Groq SSM reference when the model is empty;
  web templates with no secrets continue to render.
- `infra/aws/services/api.staging.json.tmpl`: plain `GROQ_MODEL_ID` and secret reference to
  `/group12/staging/GROQ_API_KEY`. No secret value is in the repository.
- `infra/aws/env.sh.example`, `06_services.sh`: first-time setup setting defaults empty, including
  old env.sh copies. Its pure renderer also omits the secret reference when Groq is off.
- `docs/guides/deployment.md`: Kirtan creates the SecureString before enabling the model; includes
  a placeholder command using hidden keyboard input and stdin, variable commands and a runbook
  check for `provider: GROQ`/actual model when Gemini really fails. Otherwise report recorded-test
  coverage. Do not force staging failures.
- `apps/api/tests/unit/core/test_groq_deploy.py`: offline checks execute the real setup renderer and
  both workflow jq filters with enabled/disabled model values and API/web configurations.

## Commands and results

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest -q tests/unit/core/test_groq_deploy.py tests/unit/generation/test_provider_chain.py` | `28 passed in 3.52s` |
| `bash -n infra/aws/06_services.sh` | exit 0, no output |
| `make lint` | `All checks passed!`; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 140 source files`; `✓ Types generated successfully` (exit 0) |

## Acceptance and operational follow-up

- Verified offline: optional model variables, plain environment, SSM-only key injection,
  no missing-parameter dependency with Groq off, and both workflow renderers (10 deployment cases).
- Verified by pipeline tests: Groq is observed if Gemini and its fallback fail, and rule-based
  labelling follows a Groq failure. No staging generation was run for this part.
- Not verified: creation of the single team key or the SSM parameter, repository variable values,
  hosted deployment and staging observation. These remain Kirtan's pre-deploy actions.
- As in RUN-103, `api.production.json.tmpl` is absent until IMP-801. The production workflow variable
  is wired; the runbook records the plain `PRODUCTION_GROQ_MODEL_ID` substitution and production
  secret reference to include when that template is created. Production hosting was not added.
- No AWS account command, deployment, key rotation or merge was performed. Full CI/E2E is deferred
  under operator fast mode.

Blockers: none for this repository change. Proposed decisions: none.
