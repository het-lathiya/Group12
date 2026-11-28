"""Build the course presentation with python-pptx from an external tool environment."""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INK = "16302E"
TEAL = "0F766E"
PAPER = "FAFAF9"
MUTED = "57534E"
TITLES = [
    "Title",
    "Group leader and detailed task assignment",
    "Objectives",
    "Milestones",
    "Use case diagram / user story backlog by sprint",
    "Lessons learnt",
    "Achievements",
    "Mistakes",
    "Rating of software artefacts (0–5)",
    "Overall project rating (out of 10)",
]
ASSIGNMENTS = [
    ("Nidhi · group leader", "Providers, pipeline, repair", "IMP-110 / 305 / 502"),
    ("Kirtan", "CI, deployment, limits", "IMP-102 / 217 / 511"),
    ("Manal", "Trips, budget, validation", "IMP-203 / 308 / 404"),
    ("Het", "Auth, generation jobs, edits", "IMP-108 / 210 / 407"),
    ("Junaid", "Routing, validation, security QA", "IMP-307 / 501 / 702"),
    ("Malhar", "Migrations, place data, fallback", "IMP-106 / 205 / 402"),
    ("Jeel", "ORM, retrieval, versions", "IMP-106 / 315 / 610"),
    ("Manya", "Prompts, constraints, evaluation", "IMP-111 / 406 / 514"),
    ("Manasvi", "Trip wizard, itinerary, map", "IMP-212 / 309 / 508"),
    ("Krrish", "Sign-in, keyboard, browser QA", "IMP-109 / 513 / 701"),
]


def browser_path() -> str:
    override = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if override:
        return override
    for name in ("chromium", "chromium-browser", "google-chrome"):
        if path := shutil.which(name):
            return path
    cache = Path.home() / ".cache/ms-playwright"
    matches = sorted(cache.glob("chromium-*/chrome-linux*/chrome"))
    if matches:
        return str(matches[-1])
    raise SystemExit("Set PUPPETEER_EXECUTABLE_PATH to an installed Chromium executable.")


def render_use_cases() -> Path:
    source = ROOT / "docs/course/01-requirements.md"
    section = source.read_text().split("### 4.3 Use case diagram", 1)[1]
    diagram = re.search(r"```mermaid\n(.*?)```", section, re.S)
    if diagram is None:
        raise SystemExit("The requirements use-case diagram is missing.")
    output = HERE / "use-cases.png"
    with tempfile.TemporaryDirectory(prefix="run102-mermaid-") as directory:
        work = Path(directory)
        (work / "use-cases.mmd").write_text(diagram.group(1))
        config = {"executablePath": browser_path(), "args": ["--no-sandbox"]}
        (work / "puppeteer.json").write_text(json.dumps(config))
        subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli@12.2.0",
                "-i",
                str(work / "use-cases.mmd"),
                "-o",
                str(output),
                "-p",
                str(work / "puppeteer.json"),
                "-b",
                "white",
                "--size",
                "2200",
                "-s",
                "2",
            ],
            check=True,
            env={**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "true"},
        )
    # Preserve the complete source rendering, and use a labelled excerpt at presentation scale.
    focus = HERE / "use-cases-focus.png"
    keep = {"traveller", "uc03", "uc06", "uc07", "uc08", "uc10", "uc12"}
    lines = ["flowchart LR"]
    for line in diagram.group(1).splitlines():
        identifiers = set(re.findall(r"\b(?:traveller|uc\d+)\b", line))
        if (
            identifiers
            and identifiers <= keep
            and not any(
                external in line
                for external in ("visitor", "member", "auth", "gemini", "ors", "live")
            )
        ):
            lines.append(line)
    with tempfile.TemporaryDirectory(prefix="run102-mermaid-focus-") as directory:
        work = Path(directory)
        (work / "focus.mmd").write_text("\n".join(lines) + "\n")
        (work / "puppeteer.json").write_text(json.dumps(config))
        subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli@12.2.0",
                "-i",
                str(work / "focus.mmd"),
                "-o",
                str(focus),
                "-p",
                str(work / "puppeteer.json"),
                "--size",
                "1800",
                "-s",
                "2",
            ],
            check=True,
            env={**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "true"},
        )
    return focus


def text_box(slide, x, y, width, height, text, size=24, color=INK, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.03)
    for index, line in enumerate(text.split("\n")):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = "Arial"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = RGBColor.from_string(color)
        paragraph.space_after = Pt(9)
    return shape


def base_slide(deck, number, title):
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(PAPER)
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.16), Inches(7.5))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = RGBColor.from_string(TEAL)
    stripe.line.fill.background()
    title_shape = slide.shapes.title
    title_shape.left, title_shape.top = Inches(0.55), Inches(0.62)
    title_shape.width, title_shape.height = Inches(12.1), Inches(0.85)
    title_shape.text = title
    paragraph = title_shape.text_frame.paragraphs[0]
    paragraph.font.name, paragraph.font.size = "Arial", Pt(27)
    paragraph.font.bold = True
    paragraph.font.color.rgb = RGBColor.from_string(INK)
    text_box(
        slide,
        0.58,
        0.17,
        11.5,
        0.3,
        "GROUP 12  /  IT314  /  COURSE DRAFT",
        10,
        TEAL,
        True,
    )
    text_box(
        slide,
        0.58,
        7.03,
        10.8,
        0.3,
        "Autumn 2026-27 · evidence in speaker notes · rehearsal pending",
        10,
        MUTED,
    )
    text_box(slide, 12.0, 7.0, 0.7, 0.3, f"S{number}", 11, TEAL, True)
    return slide


def definitions():
    return json.loads((HERE / "slides.json").read_text())["slides"]


def build(output: Path, diagram: Path):
    deck = Presentation()
    deck.core_properties.author = "Group 12"
    deck.core_properties.last_modified_by = "Group 12"
    deck.core_properties.subject = "IT314 Software Engineering, Autumn 2026-27"
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    for number, item in enumerate(definitions(), 1):
        slide = base_slide(deck, number, item["title"])
        kind, lines = item["kind"], item["lines"]
        if kind == "title":
            text_box(slide, 0.72, 2.0, 11.9, 1.0, lines[0], 56, TEAL, True)
            text_box(slide, 0.77, 3.3, 11.6, 0.8, lines[1], 29)
            text_box(slide, 0.77, 4.7, 11.6, 1.1, "\n".join(lines[2:]), 22, MUTED)
        elif kind == "assignments":
            for i, row in enumerate(ASSIGNMENTS):
                y = 1.67 + i * 0.48
                text_box(slide, 0.65, y, 2.65, 0.43, row[0], 16, TEAL, True)
                text_box(slide, 3.30, y, 5.15, 0.43, row[1], 16)
                text_box(slide, 8.45, y, 4.0, 0.43, row[2], 15, MUTED)
        elif kind == "diagram":
            slide.shapes.add_picture(str(diagram), Inches(0.6), Inches(1.6), height=Inches(5.2))
            text_box(slide, 7.3, 1.85, 5.2, 4.6, "\n\n".join(lines), 18)
        elif kind == "rating":
            text_box(slide, 0.85, 2.2, 11.6, 1.5, lines[0], 44, TEAL, True)
            text_box(slide, 0.85, 4.4, 11.6, 1.0, lines[1], 24, MUTED)
        else:
            for i, line in enumerate(lines):
                text_box(
                    slide,
                    0.85,
                    1.85 + i * 1.0,
                    11.6,
                    0.85,
                    line,
                    27 if kind == "bullets" else 24,
                )
        slide.notes_slide.notes_text_frame.text = item["notes"]
    assert sum(item["target_seconds"] for item in definitions()) == 300
    assert all("[team to fill]" in line for line in definitions()[8]["lines"])
    assert definitions()[9]["lines"][0] == "[team to fill]"
    deck.save(output)
    reloaded = Presentation(output)
    titles = [slide.shapes.title.text for slide in reloaded.slides]
    assert titles == TITLES, titles
    assert all(slide.notes_slide.notes_text_frame.text for slide in reloaded.slides)
    print(f"PPTX reload: {len(titles)} slides; titles in order; speaker notes present")
    print("Target slot: 300 seconds planned; rehearsal not run")
    print("Slide titles: " + " | ".join(titles))


def write_html(path: Path, diagram: Path):
    sections = []
    for number, item in enumerate(definitions(), 1):
        body = "".join(f"<p>{html.escape(line)}</p>" for line in item["lines"])
        if item["kind"] == "assignments":
            body = (
                "<table>"
                + "".join(
                    "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>"
                    for row in ASSIGNMENTS
                )
                + "</table>"
            )
        if item["kind"] == "diagram":
            body = (
                f'<img class="diagram" src="{diagram.as_uri()}" alt="Use case diagram from requirements">'
                + body
            )
        sections.append(
            f"<section data-kind='{item['kind']}'><small>GROUP 12 / IT314 / DRAFT · S{number}</small><h1>{html.escape(item['title'])}</h1><article>{body}</article><footer>Autumn 2026-27 · rehearsal pending</footer></section>"
        )
    path.write_text(
        """<!doctype html><meta charset="utf-8"><title>Group 12 course slides</title><style>
@page {size:13.333in 7.5in;margin:0}*{box-sizing:border-box}body{margin:0;background:#FAFAF9;color:#16302E;font:24pt Arial,sans-serif}section{height:7.5in;width:13.333in;padding:.35in .6in;border-left:.16in solid #0F766E;position:relative;break-after:page}section:last-child{break-after:auto}small{font-size:10pt;color:#0F766E}h1{font-size:27pt;margin:.22in 0 .35in}article p{margin:.22in 0 .4in}table{border-collapse:collapse;width:100%;font-size:16pt}td{padding:.13in .04in;border-bottom:1px solid #deded9}td:first-child{color:#0F766E;font-weight:bold}td:last-child{font-size:15pt;color:#57534E}.diagram{height:5.05in;max-width:6.5in;object-fit:contain;float:left;margin-right:.35in}section[data-kind="diagram"] article p{font-size:18pt;margin:.12in 0 .25in}section[data-kind="title"] article p:first-child{font-size:56pt;color:#0F766E;font-weight:bold}section[data-kind="rating"] article p:first-child{font-size:44pt;color:#0F766E}footer{position:absolute;bottom:.25in;font-size:10pt;color:#57534E}</style>"""
        + "".join(sections)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "Group12-IT314-slides.pptx")
    parser.add_argument("--html", type=Path)
    parser.add_argument("--reuse-diagram", action="store_true")
    args = parser.parse_args()
    diagram = HERE / "use-cases-focus.png" if args.reuse_diagram else render_use_cases()
    build(args.output, diagram)
    if args.html:
        write_html(args.html.resolve(), diagram.resolve())


if __name__ == "__main__":
    main()
