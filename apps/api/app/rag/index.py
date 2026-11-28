"""``python -m app.rag.index [--destination <slug>] [--check] [--strict]`` (Amendment A1 §6.6).

Exit codes: 0 success, 1 guide-gate errors with ``--strict``, 2 usage error, 3 embedding provider
unavailable. The report holds counts, file names, line numbers and rule names: no text, no secret.
"""

import argparse
import asyncio
import sys
from typing import Final

from app.db.session import get_engine
from app.rag import service
from app.rag.service import IndexReport, UnknownDestinationError

EXIT_USAGE: Final = 2


def report_lines(report: IndexReport) -> list[str]:
    lines = [
        f"rag-index: {finding.file}:{finding.line}: {finding.severity}: {finding.rule}"
        for finding in report.findings
    ]
    lines.append(
        f"rag-index: documents={report.documents} chunks={report.chunks} "
        f"embedded={report.embedded} inactive={report.inactive} "
        f"warnings={report.warnings} errors={report.errors}"
    )
    if report.provider_failed:
        lines.append("rag-index: embedding provider unavailable; a re-run resumes from here")
    elif report.queued:
        lines.append(f"rag-index: embedding budget spent, queued={report.queued}; a re-run resumes")
    return lines


async def _run(args: argparse.Namespace) -> IndexReport:
    try:
        return await service.index(args.destination, args.check, args.strict)
    finally:
        await get_engine().dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.rag.index", description="Build the RAG index (A1 §6.6)."
    )
    parser.add_argument("--destination", metavar="SLUG", help="one destination; default all")
    parser.add_argument("--check", action="store_true", help="validate and write nothing")
    parser.add_argument("--strict", action="store_true", help="gate warnings become errors")
    args = parser.parse_args(argv)
    try:
        report = asyncio.run(_run(args))
    except UnknownDestinationError:
        print("rag-index: --destination names no active destination", file=sys.stderr)
        return EXIT_USAGE
    print("\n".join(report_lines(report)))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
