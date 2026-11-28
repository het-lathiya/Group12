"""Summarize downloaded course coverage artifacts without rounding intermediate totals."""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def percentage(covered: int, total: int) -> str:
    return f"{100 * covered / total:.2f}%" if total else "n/a"


def row(name: str, values: list[int]) -> str:
    lines, total_lines, branches, total_branches = values
    return (
        f"| {name} | {lines}/{total_lines} ({percentage(lines, total_lines)}) "
        f"| {branches}/{total_branches} ({percentage(branches, total_branches)}) |"
    )


def table(title: str, groups: dict[str, list[int]]) -> None:
    print(f"\n{title}\n")
    print("| Package | Lines covered/total (%) | Branches covered/total (%) |")
    print("| --- | --- | --- |")
    for name, values in sorted(groups.items()):
        print(row(name, values))
    print(row("TOTAL", [sum(v[i] for v in groups.values()) for i in range(4)]))


def summarize(root: Path, run_url: str, commit: str) -> None:
    print(f"Source: {run_url}\nCommit measured: {commit}")
    print("Artifacts: coverage-api, coverage-web (downloaded outside the repository)")
    print("Percentages = covered / total * 100; n/a = no instrumented branches.")
    api = json.loads((root / "coverage-api/coverage.json").read_text())
    groups: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    gaps = []
    for name, data in sorted(api["files"].items()):
        parts = Path(name).parts
        package = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        s = data["summary"]
        values = [
            s["covered_lines"],
            s["num_statements"],
            s["covered_branches"],
            s["num_branches"],
        ]
        groups[package] = [a + b for a, b in zip(groups[package], values, strict=True)]
        if s["missing_lines"] or s["missing_branches"]:
            gaps.append(
                f"{name}: missing_lines={s['missing_lines']}; missing_branches={s['missing_branches']}"
            )
    table("API", groups)
    total = api["totals"]
    print(
        f"API_TOTAL lines={total['covered_lines']}/{total['num_statements']} "
        f"({percentage(total['covered_lines'], total['num_statements'])}); "
        f"branches={total['covered_branches']}/{total['num_branches']} "
        f"({percentage(total['covered_branches'], total['num_branches'])})"
    )
    print("\nAPI uncovered modules (executable lines or branches):")
    print("\n".join(gaps) or "none")

    web = json.loads((root / "coverage-web/report/coverage-summary.json").read_text())
    groups = defaultdict(lambda: [0, 0, 0, 0])
    gaps = []
    for name, data in sorted(web.items()):
        if name == "total":
            continue
        relative = name.split("/apps/web/", 1)[-1]
        parts = Path(relative).parts
        package = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        values = [
            data["lines"]["covered"],
            data["lines"]["total"],
            data["branches"]["covered"],
            data["branches"]["total"],
        ]
        groups[package] = [a + b for a, b in zip(groups[package], values, strict=True)]
        missing_lines = data["lines"]["total"] - data["lines"]["covered"]
        missing_branches = data["branches"]["total"] - data["branches"]["covered"]
        if missing_lines or missing_branches:
            gaps.append(
                f"{relative}: missing_lines={missing_lines}; missing_branches={missing_branches}"
            )
    table("WEB", groups)
    s = web["total"]
    print(
        f"WEB_TOTAL lines={s['lines']['covered']}/{s['lines']['total']} "
        f"({percentage(s['lines']['covered'], s['lines']['total'])}); "
        f"branches={s['branches']['covered']}/{s['branches']['total']} "
        f"({percentage(s['branches']['covered'], s['branches']['total'])})"
    )
    print("\nWeb uncovered modules (executable lines or branches):")
    print("\n".join(gaps) or "none")
    for filename in [
        "coverage-api/pytest-summary.txt",
        "coverage-web/vitest-summary.txt",
    ]:
        print(f"\nOriginal terminal summary: {filename}\n")
        # Test counts and terminal coverage summary are preserved, without the progress listing.
        for line in (root / filename).read_text().splitlines():
            line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
            if re.search(
                r"^=+ .*\bpassed\b|^\s*(Test Files|Tests)\s+|^TOTAL\s+|^All files\s*\|",
                line,
            ):
                print(line.rstrip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    summarize(args.artifacts, args.run_url, args.commit)
