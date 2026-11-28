# RUN-103 · aws-fallback-runbook (IMD-222, IMD-221)

- Run: RUN-103 · Owner: Kirtan · Status: PR open · Base commit: 57b620901ff610900ce46c004a27bcae68cc695e
- Points: 0 (operations run)

## Changed files

- `infra/aws/services/api.staging.json.tmpl`: `GEMINI_FALLBACK_MODEL_ID=${STAGING_GEMINI_FALLBACK_MODEL_ID}` (plain environment)
- `.github/workflows/deploy-staging.yml`, `deploy-production.yml`: `<ENV>_GEMINI_FALLBACK_MODEL_ID` from repository variables; unset renders as empty, not required by the check job
- `infra/aws/env.sh.example`, `infra/aws/06_services.sh`: optional `STAGING_GEMINI_FALLBACK_MODEL_ID` (an older `env.sh` without it still renders)
- `docs/secrets.md`, `docs/guides/aws-setup.md`, `docs/guides/deployment-guide.md`: variable documented; production kept up until evaluation ends
- `docs/guides/deployment.md` §8.1: course demo window runbook

## Commands

- `actionlint .github/workflows/deploy-staging.yml .github/workflows/deploy-production.yml`: no output (0 errors)
- `shellcheck -x -S warning infra/aws/06_services.sh`: no output
- `envsubst < infra/aws/services/api.staging.json.tmpl | jq` with the variable empty: `{"name":"GEMINI_FALLBACK_MODEL_ID","value":""}`
- `pytest -q tests/unit/core/test_config.py tests/unit/ai/test_factory.py`: `68 passed, 1 warning in 9.40s`
- `make lint`: `All checks passed!`, `271 files already formatted`, `All matched files use Prettier code style!`

## Acceptance

- Fallback ID wired for staging and production, optional, no value in the repository: verified (template render with empty value; workflow check job does not require it).
- Runbook before/in/after window, course rule, cost check, teardown, live URL: verified by review of `deployment.md` §8.1.
- Any deploy or AWS step: not verified, run by Kirtan.

## Blockers and open issues

- The production template `infra/aws/services/api.production.json.tmpl` does not exist yet (IMP-801); it must carry the same `GEMINI_FALLBACK_MODEL_ID=${PRODUCTION_GEMINI_FALLBACK_MODEL_ID}` line.
- Forcing the fallback on staging: an invalid primary model ID is a bad request and does not trigger the fallback (PD-RUN-100-1), so the runbook does not use it.

## Proposed decisions

- PD-RUN-103-1: hold the fallback model ID as a repository variable rendered into plain environment, not an SSM parameter: a missing SSM parameter in ECS `secrets` stops the task, and the value is not secret.
- PD-RUN-103-2: if a staging check of the fallback path is wanted, a staging-only way to make the primary return 503 needs a code change and a decision; until then, provider unit tests cover it.
