"""Run record of the evaluation harness (§8.17; IMP-413, IMP-514).

``eval/results/<run_id>/run.json`` names what produced the scores: dataset and its hash, provider,
model, prompt template with the sha256 of its files, schema versions, settings sent, metrics, case
count, failures, git commit and times. It never holds a key, a prompt body or a model answer.
``write`` refuses a record that lacks a required field (FR-120, TC-390).
"""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Final

from app.ai.prompts.registry import PromptTemplate
from app.schemas.ai import ModelMetadata


class DatasetError(Exception):
    """The dataset cannot be read or does not match its manifest."""


class IncompleteRecordError(Exception):
    """A run record lacks a required field; nothing is written."""


# A field is missing when it is absent or null; an empty value ({} settings, [] failures) is valid.
REQUIRED_FIELDS: Final = (
    "run_id",
    "started_at",
    "git_commit",
    "dataset_id",
    "dataset_version",
    "provider",
    "model_id",
    "prompt_template_id",
    "prompt_version",
    "input_schema_version",
    "output_schema_version",
    "generation_settings",
    "metrics",
    "case_count",
    "failures",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(folder: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The dataset manifest and its cases, after checking the hash of ``cases.jsonl``."""
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        cases_file = folder / "cases.jsonl"
        lines = cases_file.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError) as exc:
        raise DatasetError(f"cannot read dataset {folder}: {exc}") from None
    if manifest.get("files", {}).get("cases.jsonl") != sha256(cases_file):
        raise DatasetError(f"{cases_file} does not match the hash in its manifest")
    return manifest, [json.loads(line) for line in lines if line.strip()]


def git_commit() -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, nothing from input
            [git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip()


def build(
    *,
    run_id: str,
    dataset: dict[str, Any],
    provider: str,
    metadata: ModelMetadata | None,
    template: PromptTemplate,
    prompt_version_overridden: bool,
    settings_sent: dict[str, Any],
    repeats: int,
    metrics_file: Path,
    started_at: str,
    ended_at: str,
    metrics: dict[str, Any],
    case_count: int,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["version"],
        "dataset_sha256": dataset["set_sha256"],
        "provider": provider,
        "model_id": metadata.model_id if metadata else None,
        "model_version": metadata.model_version if metadata else None,
        "adapter_version": metadata.adapter_version if metadata else None,
        "prompt_template_id": template.template_id,
        "prompt_version": template.version,
        "prompt_sha256": dict(template.sha256),
        "prompt_version_overridden": prompt_version_overridden,
        "input_schema_version": template.meta.input_schema_version,
        "output_schema_version": template.meta.output_schema_version,
        "generation_settings": settings_sent,
        "repeats": repeats,
        "metrics_version": metrics["metrics_version"],
        "metrics_definition_sha256": sha256(metrics_file),
        "git_commit": git_commit(),
        "started_at": started_at,
        "ended_at": ended_at,
        "metrics": metrics,
        "case_count": case_count,
        "failures": failures,
    }


def write(path: Path, record: dict[str, Any]) -> None:
    """Write ``record`` as JSON; IncompleteRecordError, and no file, if a required field is missing."""
    missing = [name for name in REQUIRED_FIELDS if record.get(name) is None]
    if missing:
        raise IncompleteRecordError(f"run record lacks {', '.join(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
