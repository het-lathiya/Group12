"""Build an inspected draft submission from one immutable git commit."""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile("AI" + "za" + "|" + "AK" + "IA" + "|" + r"(?<![A-Za-z0-9_])" + "s" + "k-")
DOCUMENTS = [1, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 15]
# Non-code historical audit examples contain literal scanner prefixes; never rewrite them.
AUDIT_EXAMPLES = {
    "docs/progress/parts/IMP-514-gemini-baseline.md",
    "docs/progress/parts/IMP-705-whole-task.md",
    "docs/progress/parts/IMP-732-gemini-v4-result.md",
    "eval/reports/final-baseline.md",
}


def unsafe_path(name):
    parts = PurePosixPath(name).parts
    if not parts or name.startswith("/") or ".." in parts:
        return True
    for component in parts:
        lower = component.lower()
        if lower.startswith(".env") or lower.endswith(".pem") or "secret" in lower:
            return True
        if lower in {"node_modules", ".venv", "mutants", "dist", ".git"}:
            return True
    return False


def inspect_text(text, name):
    if KEY_PATTERN.search(text):
        raise ValueError(f"Provider/access-key prefix found in {name}; value withheld")


def inspect_file(path, name):
    if path.is_symlink():
        raise ValueError(f"Symbolic link is not allowed in payload: {name}")
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        if not reader.pages:
            raise ValueError(f"Empty PDF: {name}")
        for page in reader.pages:
            inspect_text(page.extract_text() or "", name)
    elif path.suffix.lower() in {".pptx", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if unsafe_path(member.filename):
                    raise ValueError(f"Unsafe nested archive path in {name}")
                if member.filename.endswith((".xml", ".rels", ".txt", ".json")):
                    inspect_text(archive.read(member).decode("utf-8", errors="replace"), name)
    else:
        raw = path.read_bytes()
        if b"\0" not in raw[:4096]:
            inspect_text(raw.decode("utf-8", errors="replace"), name)


def inspect_stage(stage):
    files = []
    for path in sorted(stage.rglob("*")):
        name = path.relative_to(stage).as_posix()
        if unsafe_path(name):
            raise ValueError(f"Unsafe payload path: {name}")
        if path.is_file() or path.is_symlink():
            inspect_file(path, name)
            files.append(path)
    print(f"Submission safety check: PASS ({len(files)} files checked)")
    return files


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def export_source(commit, stage):
    raw = git_output("ls-tree", "-rz", "--name-only", commit)
    names = [s.decode() for s in raw.split(b"\0") if s]
    allowed = [name for name in names if not unsafe_path(name) and name not in AUDIT_EXAMPLES]
    if not allowed:
        raise ValueError("The selected commit has no exportable source")
    archive = git_output("archive", "--format=tar", "--prefix=source/", commit, "--", *allowed)
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        for member in contents.getmembers():
            if unsafe_path(member.name) or member.issym() or member.islnk():
                raise ValueError(f"Unsafe git archive member: {member.name}")
        contents.extractall(stage, filter="data")
    source = stage / "source"
    exported = sum(path.is_file() for path in source.rglob("*"))
    return source, exported, len(names) - exported


def pdf_command(source, output, renderer, slides=False):
    # npx supplies a fixed renderer and its tools; paths are argument-array elements.
    subprocess.run(
        [
            "npx",
            "--yes",
            "--package=@mermaid-js/mermaid-cli@12.2.0",
            "--package=marked@18.3.0",
            "-c",
            'node "$COURSE_RENDERER" "$COURSE_INPUT" "$COURSE_OUTPUT" $COURSE_SLIDES',
        ],
        check=True,
        env={
            **os.environ,
            "PUPPETEER_SKIP_DOWNLOAD": "true",
            "COURSE_RENDERER": str(renderer),
            "COURSE_INPUT": str(source),
            "COURSE_OUTPUT": str(output),
            "COURSE_SLIDES": "--slides" if slides else "",
        },
    )


def course_map(source):
    course = source / "docs/course"
    found = {}
    for path in course.glob("[0-9][0-9]-*.md"):
        number = int(path.name[:2])
        if number in found:
            raise ValueError(f"Duplicate course item {number}")
        found[number] = path
    missing = sorted(set(DOCUMENTS) - set(found))
    if missing:
        raise ValueError(
            f"Course items absent at selected ref: {missing}; select a merged course ref"
        )
    return found


def build(args):
    commit = (
        git_output("rev-parse", "--verify", "--end-of-options", args.ref + "^{commit}")
        .decode()
        .strip()
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="group12-submission-") as temporary:
        work = Path(temporary)
        stage = work / "payload"
        stage.mkdir()
        source, source_count, excluded_count = export_source(commit, stage)
        # Inspect the filtered git archive before starting any rendering tool.
        inspect_stage(source)
        renderer = source / "scripts/render_course_pdf.mjs"
        documents = course_map(source)
        course = stage / "course"
        course.mkdir()
        mapping = {}
        for number in DOCUMENTS:
            path = documents[number]
            pdf = course / (path.stem + ".pdf")
            pdf_command(path, pdf, renderer)
            mapping[pdf.relative_to(stage).as_posix()] = f"{number:02d} {path.stem[3:]}"
        sprint_dir = source / "docs/course/02-sprints"
        sprint_paths = sorted(sprint_dir.glob("sprint-*.md"))
        if [p.stem for p in sprint_paths] != [f"sprint-{i}" for i in range(1, 9)]:
            raise ValueError("The selected ref must contain the complete sprint document set")
        (course / "02-sprints").mkdir()
        for path in sprint_paths:
            pdf = course / "02-sprints" / (path.stem + ".pdf")
            pdf_command(path, pdf, renderer)
            mapping[pdf.relative_to(stage).as_posix()] = "02 Sprint details — " + path.stem
        slides_dir = source / "docs/course/14-slides"
        slide_html = work / "slides.html"
        rebuilt_deck = work / "slides.pptx"
        subprocess.run(
            [
                sys.executable,
                str(slides_dir / "build_slides.py"),
                "--reuse-diagram",
                "--output",
                str(rebuilt_deck),
                "--html",
                str(slide_html),
            ],
            check=True,
        )
        shutil.copy2(rebuilt_deck, course / "Group12-IT314-slides.pptx")
        mapping["course/Group12-IT314-slides.pptx"] = "14 Course slides — editable deck"
        pdf_command(slide_html, course / "14-slides.pdf", renderer, slides=True)
        mapping["course/14-slides.pdf"] = "14 Course slides — printable view"
        reports = source / "docs/test-reports/course"
        if not reports.is_dir():
            raise ValueError("Course test-report evidence is absent at the selected ref")
        shutil.copytree(reports, stage / "test-reports/course")
        shutil.copytree(source / "docs/spec", stage / "docs/spec")
        coverage_inputs = []
        for kind, explicit, candidate in [
            ("api", args.coverage_api_dir, ROOT / "apps/api/course-coverage/html"),
            ("web", args.coverage_web_dir, ROOT / "apps/web/course-coverage/report"),
        ]:
            selected = explicit if explicit else candidate if candidate.is_dir() else None
            if selected is not None:
                if not (selected / "index.html").is_file():
                    raise ValueError(f"Coverage {kind} input has no index.html")
                shutil.copytree(selected, stage / "test-reports" / ("coverage-" + kind))
                coverage_inputs.append({"kind": kind, "input": str(selected.resolve())})
        (stage / "LINKS.txt").write_text(
            "Live URL: [team to fill]\nYouTube link: [team to fill]\nRepository URL: [team to fill]\n"
        )
        metadata = {
            "ref": args.ref,
            "commit": commit,
            "source_files": source_count,
            "excluded_source_paths": excluded_count,
            "coverage_html_inputs": coverage_inputs,
            "coverage_run_url": args.coverage_run_url,
            "excluded_audit_examples": sorted(AUDIT_EXAMPLES),
            "status": "draft; team ratings, signatures, URLs and rehearsal remain to be completed",
        }
        (stage / "BUILD.json").write_text(json.dumps(metadata, indent=2) + "\n")
        index = [
            "Group 12 · IT314 · Autumn 2026-27 · DRAFT submission",
            f"Selected ref: {args.ref}; commit: {commit}",
            f"10 Source code → source/ (git archive of {args.ref}, commit {commit})",
            "No PDF is expected for item 10 (RUN-102 clarification).",
            "Source exclusions: environment/key paths, generated directories, and these non-code audit examples:",
            *sorted(AUDIT_EXAMPLES),
            "Coverage HTML provenance: "
            + (args.coverage_run_url or "not supplied; see BUILD.json"),
            "",
            "File → course item / purpose",
        ]
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            name = path.relative_to(stage).as_posix()
            category = mapping.get(name)
            if category is None:
                category = (
                    "10 Source code"
                    if name.startswith("source/")
                    else "Specification"
                    if name.startswith("docs/spec/")
                    else "Testing evidence"
                    if name.startswith("test-reports/")
                    else "Submission links / provenance"
                )
            index.append(name + " → " + category)
        index.append("INDEX.txt → Submission index")
        (stage / "INDEX.txt").write_text("\n".join(index) + "\n")
        files = inspect_stage(stage)
        pending = output.with_suffix(".zip.pending")
        try:
            with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in files:
                    archive.write(path, path.relative_to(stage).as_posix())
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise ValueError("ZIP integrity check failed")
                names = archive.namelist()
                if any(unsafe_path(name) for name in names):
                    raise ValueError("ZIP contains a forbidden path")
            pending.replace(output)
        finally:
            pending.unlink(missing_ok=True)
        output.with_suffix(".files.txt").write_text("\n".join(names) + "\n")
        summary = {
            **metadata,
            "zip": str(output),
            "files": len(names),
            "pdfs": sum(name.startswith("course/") and name.endswith(".pdf") for name in names),
            "bytes": output.stat().st_size,
        }
        output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("Submission ZIP: " + str(output))
        print(
            f"Submission result: files={summary['files']} course_pdfs={summary['pdfs']} source_files={source_count} bytes={summary['bytes']}"
        )
        print("File list: " + str(output.with_suffix(".files.txt")))
        print("ZIP integrity: PASS; forbidden paths: none; key-prefix scan: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", nargs="?", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/12.zip")
    parser.add_argument("--coverage-api-dir", type=Path)
    parser.add_argument("--coverage-web-dir", type=Path)
    parser.add_argument("--coverage-run-url", default="")
    parser.add_argument(
        "--check-only", type=Path, help="Inspect an already staged directory without rendering"
    )
    args = parser.parse_args()
    try:
        if args.check_only:
            inspect_stage(args.check_only.resolve())
        else:
            build(args)
    except (
        ValueError,
        subprocess.CalledProcessError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as error:
        raise SystemExit(f"Submission build refused: {error}") from error


if __name__ == "__main__":
    main()
