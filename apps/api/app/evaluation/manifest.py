"""Run record of the evaluation harness (§8.17, card step 4; IMP-413).

``eval/results/<run_id>/run.json`` names what produced the scores: dataset and its hash, provider,
model, prompt template, schema versions, settings sent, metrics version, git commit and times. It
never holds a key, a prompt body or a model answer.
"""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.schemas.ai import OUTPUT_SCHEMA_VERSION, ModelMetadata


class DatasetError(Exception):
    """The dataset cannot be read or does not match its manifest."""


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
    prompt: tuple[str, str],
    settings_sent: dict[str, Any],
    repeats: int,
    metrics_file: Path,
    started_at: str,
    ended_at: str,
    metrics: dict[str, Any],
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
        "prompt_template_id": prompt[0],
        "prompt_version": prompt[1],
        "input_schema_version": "gr-1",
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "generation_settings": settings_sent,
        "repeats": repeats,
        "metrics_version": metrics["metrics_version"],
        "metrics_definition_sha256": sha256(metrics_file),
        "git_commit": git_commit(),
        "started_at": started_at,
        "ended_at": ended_at,
        "metrics": metrics,
    }
