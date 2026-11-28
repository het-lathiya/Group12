"""Print per-module mutation counts from mutmut metadata or a Stryker JSON report."""

import argparse
import json
from collections import Counter
from pathlib import Path

COLUMNS = ("Killed", "Survived", "Timeout", "NoCoverage", "Error", "NotRun")


def report(rows: dict[str, Counter[str]], label: str) -> None:
    print(
        "| Module | Killed | Survived | Timeout | No coverage | Error | Not run | Score |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    total: Counter[str] = Counter()
    for counts in rows.values():
        total.update(counts)
    for name, counts in [*sorted(rows.items()), ("TOTAL", total)]:
        denominator = sum(counts.values())
        score = (
            f"{100 * (counts['Killed'] + counts['Timeout']) / denominator:.2f}%"
            if denominator and not counts["Error"] and not counts["NotRun"]
            else "not reported"
        )
        print(
            f"| {name} | "
            + " | ".join(str(counts[c]) for c in COLUMNS)
            + f" | {score} |"
        )
        if name == "TOTAL":
            print(
                f"{label}_TOTAL killed={counts['Killed']} survived={counts['Survived']} "
                f"timeout={counts['Timeout']} no_coverage={counts['NoCoverage']} "
                f"error={counts['Error']} not_run={counts['NotRun']} score={score}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["api", "web"])
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    rows: dict[str, Counter[str]] = {}
    if args.kind == "api":
        statuses = {
            0: "Survived",
            1: "Killed",
            33: "NoCoverage",
            5: "NoCoverage",
            36: "Timeout",
            -24: "Timeout",
            24: "Timeout",
            152: "Timeout",
            255: "Timeout",
            None: "NotRun",
        }
        for path in sorted(args.source.rglob("*.py.meta")):
            data = json.loads(path.read_text())
            rows[str(path.relative_to(args.source)).removesuffix(".meta")] = Counter(
                statuses.get(code, "Error")
                for code in data["exit_code_by_key"].values()
            )
    else:
        data = json.loads(args.source.read_text())
        for name, file in data["files"].items():
            rows[name] = Counter(
                mutant["status"] if mutant["status"] in COLUMNS else "Error"
                for mutant in file["mutants"]
            )
    if not rows:
        raise SystemExit("No mutation results found")
    report(rows, args.kind.upper())


if __name__ == "__main__":
    main()
