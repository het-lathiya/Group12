"""Render real deployment templates offline: disabled Groq must not require an SSM key."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from string import Template

import pytest

ROOT = Path(__file__).resolve().parents[5]
API_TEMPLATE = ROOT / "infra/aws/services/api.staging.json.tmpl"
WEB_TEMPLATE = ROOT / "infra/aws/services/web.staging.json.tmpl"


def environment(template: str, model: str) -> dict[str, str]:
    names = re.findall(r"\$\{([A-Z0-9_]+)\}", template)
    return {
        "PATH": os.environ["PATH"],
        **dict.fromkeys(names, "test-placeholder"),
        "STAGING_GROQ_MODEL_ID": model,
    }


@pytest.mark.parametrize("model", ["", "openai/gpt-oss-20b"])
def test_setup_renderer_keeps_the_groq_secret_optional(model: str) -> None:
    source = (ROOT / "infra/aws/06_services.sh").read_text()
    start = source.index("render() {")
    render = source[start : source.index("\n}\n", start) + 3]
    # Only the pure renderer is extracted; none of the account-facing script is run.
    result = subprocess.run(  # noqa: S603  # fixed local helper, synthetic env only
        ["bash", "-c", render + '\nrender "$1"', "render-test", str(API_TEMPLATE)],  # noqa: S607
        env=environment(API_TEMPLATE.read_text(), model),
        text=True,
        capture_output=True,
        check=True,
    )
    container = json.loads(result.stdout)["primaryContainer"]
    assert (
        next(e["value"] for e in container["environment"] if e["name"] == "GROQ_MODEL_ID") == model
    )
    secret = next((s for s in container["secrets"] if s["name"] == "GROQ_API_KEY"), None)
    assert (secret is not None) == bool(model)
    if secret is not None:
        assert secret["valueFrom"].endswith("parameter/group12/staging/GROQ_API_KEY")
    assert all(e["name"] != "GROQ_API_KEY" for e in container["environment"])


@pytest.mark.parametrize("deploy_env", ["staging", "production"])
@pytest.mark.parametrize("model", ["", "openai/gpt-oss-20b"])
@pytest.mark.parametrize("kind", ["api", "web"])
def test_workflow_renderers_allow_missing_groq_and_web_secrets(
    deploy_env: str, model: str, kind: str
) -> None:
    jq = shutil.which("jq")
    assert jq is not None, "deploy template checks need jq, as the deploy workflows do"
    workflow = (ROOT / f".github/workflows/deploy-{deploy_env}.yml").read_text()
    variable = f"{deploy_env.upper()}_GROQ_MODEL_ID"
    assert f"{variable}: ${{{{ vars.{variable} }}}}" in workflow
    query = re.search(r"\| jq --arg arn \"\$arn\" '(.*?)' > \"\$input\"", workflow, re.DOTALL)
    assert query is not None
    template = (API_TEMPLATE if kind == "api" else WEB_TEMPLATE).read_text()
    payload = Template(template).substitute(environment(template, model))
    result = subprocess.run(  # noqa: S603  # actual local jq filter; synthetic JSON on stdin
        [jq, "--arg", "arn", "test-service", query[1]],
        input=payload,
        text=True,
        capture_output=True,
        check=True,
    )
    container = json.loads(result.stdout)["primaryContainer"]
    names = {secret["name"] for secret in container.get("secrets", [])}
    assert ("GROQ_API_KEY" in names) == bool(model and kind == "api")
