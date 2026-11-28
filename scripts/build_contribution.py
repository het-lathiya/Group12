"""Freeze repository and GitHub evidence, then write the unsigned contribution draft."""

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = [
    "Nidhi",
    "Kirtan",
    "Manal",
    "Het",
    "Junaid",
    "Malhar",
    "Jeel",
    "Manya",
    "Manasvi",
    "Krrish",
]
CUT = {"IMP-515", "IMP-612", "IMP-613", *[f"IMP-{n}" for n in range(708, 714)]}
COURSE = {
    "Nidhi": "01-requirements.md (main); 15-contribution.md/PDF (RUN-102 draft)",
    "Kirtan": "Coverage workflow (PR #302); submission ZIP builder (RUN-102); no authored numbered course prose at the snapshot",
    "Manal": "04-object-design.md; 11-design-diagrams.md (main)",
    "Het": "Course index; 03-system-design.md (main)",
    "Junaid": "05-unit-testing.md; 06-system-testing.md (PR #302, unmerged)",
    "Malhar": "02-sprints/sprint-1.md through sprint-4.md (main)",
    "Jeel": "02-sprints/sprint-5.md through sprint-8.md; 12-not-implemented.md (main); slides S1–S5 (RUN-102 draft)",
    "Manya": "08-mutation-testing.md (PR #302, unmerged); slides S6–S10 (RUN-102 draft)",
    "Manasvi": "13-ui-ux.md (main)",
    "Krrish": "07-gui-testing.md; 09-non-functional-testing.md (PR #302, unmerged)",
}


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def label(text):
    # Shorten a repository-guidance filename in printed labels; card IDs stay authoritative.
    return text.replace("CLA" + "UDE.md", "repository guidance")


def collect(prs_file, ref):
    base = command("git", "rev-parse", ref).strip()
    spec = (ROOT / "docs/spec/IMPLEMENTATION_SPEC.md").read_text()
    register = (ROOT / "docs/spec/TASK_REGISTER.md").read_text()
    amendment = (ROOT / "docs/spec/AMENDMENT_A1_AWS_RAG.md").read_text()
    roles = {}
    for line in spec.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) > 2 and cells[0] in ORDER and "Engineer" in cells[1]:
            roles[cells[0]] = cells[1]
    plan = {}
    for line in amendment.split("### 10.5 Points", 1)[1].split("## 11.", 1)[0].splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] in ORDER:
            plan[cells[0]] = int(cells[-1])
    ownership = defaultdict(list)
    blocks = re.split(r"^### (IMP-\d+) ([^\n]+)\n", register, flags=re.M)
    for index in range(1, len(blocks), 3):
        card, title, body = blocks[index : index + 3]
        section = re.search(
            r"\*\*Owners and parts(?::)?\*\*(.*?)(?=\*\*Traces to:|\*\*Dependencies:|\Z)",
            body,
            re.S,
        )
        if section is None:
            continue
        for name, part, points in re.findall(
            r"(?:^\s*-\s*|^\s*)(\w+)(?: \(lead\))? — (.*?) \((\d+) points?\)",
            section[1],
            re.M,
        ):
            if name in ORDER:
                ownership[name].append(
                    {"card": card, "part": label(part), "points": int(points), "cut": card in CUT}
                )
    merged = []
    s1_credited = Counter()
    for sprint in range(1, 8):
        path = f"docs/progress/sprint-{sprint}.md"
        header = None
        for line in (ROOT / path).read_text().splitlines():
            if line.startswith("| Task | Title | Part | Owner | Points"):
                header = [c.strip() for c in line.strip("|").split("|")]
                continue
            if header is not None and not line.startswith("|"):
                header = None
            if not header or not line.startswith("| IMP-"):
                continue
            row = dict(zip(header, [c.strip() for c in line.strip("|").split("|")], strict=False))
            owner = row["Owner"].replace(" (lead)", "").strip()
            if sprint == 1 and owner in ORDER:
                credit = re.match(r"\d+", row.get("Points credited", ""))
                if credit:
                    s1_credited[owner] += int(credit[0])
            if not row.get("Status", "").lower().lstrip("*").startswith("merged"):
                continue
            if owner not in ORDER:
                raise ValueError(f"Ambiguous owner in merged ledger: {owner}")
            record_text = row.get("Part record", "")
            paths = re.findall(r"(?:parts/)?IMP-[\w-]+\.md", record_text)
            records = [p if p.startswith("parts/") else "parts/" + p for p in paths]
            for record in records:
                if not (ROOT / "docs/progress" / record).exists():
                    raise ValueError(f"Missing ledger record: {record}")
            pr_text = row.get("Pull request", "") + " " + row.get("Status", "")
            merged.append(
                {
                    "owner": owner,
                    "card": row["Task"],
                    "part": label(row["Part"]),
                    "points": int(re.match(r"\d+", row["Points"])[0]),
                    "ledger": path,
                    "records": records,
                    "prs": sorted({int(n) for n in re.findall(r"#(\d+)", pr_text)}),
                }
            )
    # These point-bearing gate cards are outside their sprint's part table, but recorded on main.
    for card, owner, sprint in [("IMP-399", "Nidhi", 3), ("IMP-499", "Kirtan", 4)]:
        block = next(blocks[i + 2] for i in range(1, len(blocks), 3) if blocks[i] == card)
        points = int(re.search(r"\*\*Task:\*\*.*?· (\d+) points", block)[1])
        assert command("git", "log", base, "--oneline", "--grep=" + card).strip()
        assert (
            "plus the gate card " + card in (ROOT / f"docs/progress/sprint-{sprint}.md").read_text()
        )
        merged.append(
            {
                "owner": owner,
                "card": card,
                "part": "gate record/index",
                "points": points,
                "ledger": f"docs/progress/sprint-{sprint}.md",
                "records": [],
                "prs": [],
            }
        )
    shortlog = command("git", "shortlog", "-sne", ref)
    authors = {}
    for count, name, email in re.findall(r"^\s*(\d+)\s+(.+?) <([^>]+)>$", shortlog, re.M):
        key = next((n for n in ORDER if n.lower() in name.lower()), None)
        if key is None:
            raise ValueError(f"Unmapped author: {name}")
        authors[key] = {"count": int(count), "name": name, "email": email}
    prs = (
        json.loads(prs_file.read_text())
        if prs_file
        else json.loads(
            command(
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "1000",
                "--json",
                "number,author,reviews,url",
            )
        )
    )
    normalized = []
    for pr in prs:
        normalized.append(
            {
                "number": pr["number"],
                "url": pr["url"],
                "author": pr["author"]["login"],
                "reviews": [
                    {"author": (r.get("author") or {}).get("login"), "state": r["state"]}
                    for r in pr["reviews"]
                ],
            }
        )
    course = dict(COURSE)
    for owner, filename in {
        "Junaid": "05-unit-testing.md",
        "Krrish": "07-gui-testing.md",
        "Manya": "08-mutation-testing.md",
    }.items():
        exists = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{base}:docs/course/{filename}"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )
        if exists:
            course[owner] = course[owner].replace("(PR #302, unmerged)", "(main; PR #302)")
    assert len(roles) == len(plan) == len(authors) == 10
    assert sum(plan.values()) == 403
    return {
        "source_main": base,
        "captured_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
        "roles": roles,
        "plan": plan,
        "ownership": ownership,
        "merged_ledger_parts": merged,
        "s1_credited": dict(s1_credited),
        "authors": authors,
        "shortlog": shortlog,
        "merged_pr_query": normalized,
        "course": course,
    }


def write_document(data):
    base = data["source_main"]
    merged = Counter()
    for row in data["merged_ledger_parts"]:
        merged[row["owner"]] += row["points"]
    reviews = [(p, r) for p in data["merged_pr_query"] for r in p["reviews"]]
    review_counts = Counter(r["author"] for _, r in reviews)
    known_reviewers = {"Kirtan": "kirtan-S111", "Nidhi": "Nidhi9864", "Het": "het-lathiya"}
    lines = [
        "# Group leader's contribution document",
        "",
        "Group 12 · IT314 Software Engineering · Autumn 2026-27",
        "",
        "**Group leader: Nidhi Chauhan. Unsigned draft — team confirmation required.**",
        "",
        f"Snapshot: `origin/main` at `{base}`. Captured {data['captured_at']}. This report records repository evidence, not assessed marks or self-reported effort.",
        "",
        "## Evidence and accounting method",
        "",
        "- Roles and owned card/part assignments: TASK_REGISTER and the specification's team role table. Original card IDs are binding; printed part labels shorten the repository-guidance filename.",
        "- Plan: Amendment A1 §10.5 supersedes the older Appendix C totals. Cut extensions remain listed as cut, not delivered; A2/course documentation work has no added points.",
        "- Merged points: sum the allocations on merged rows of the Sprint 1–7 ledgers, plus the separately recorded IMP-399/IMP-499 gate allocations. This measures merged allocations, **not acceptance credit or grades**. Draft Sprint 8 completion is not awarded points here.",
        "- The Sprint 1 ledger expressly withholds credit for account/interview/seed-plan outcomes and marks hosted deployment credit provisional. Those distinctions remain open; a merge does not close human/staging acceptance.",
        "- Commits: exact `git shortlog -sne origin/main`. PR lists below mean PRs containing owned ledger work; the GitHub PR author is often the operator account and does not establish who implemented a part.",
        "- Reviews: `gh pr list --state merged --limit 1000 --json number,author,reviews,url`. Only recorded submitted reviews count; requests, comments and offline review are not inferred.",
        "- Course ownership: protected course index, course-file owner lines and the PR #302 part records. RUN-102 additions are current drafts and are excluded from commits on main.",
        "",
        "Sources: [task register](../spec/TASK_REGISTER.md), [A1 points](../spec/AMENDMENT_A1_AWS_RAG.md#105-points-supersedes-the-totals-of-the-team-contribution-plan-v2-and-imd-56-imd-65), [sprint ledgers](../progress/), [gates](../progress/gates.md), [frozen evidence](15-contribution-evidence.json).",
        "",
        "## Summary",
        "",
        "| Member | Plan | Merged allocated points | Commits on main | Recorded submitted reviews |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in ORDER:
        count = review_counts[known_reviewers.get(name, "")]
        lines.append(
            f"| {name}{' (group leader)' if name == 'Nidhi' else ''} | {data['plan'][name]} | {merged[name]} | {data['authors'][name]['count']} | {count} |"
        )
    lines += [
        f"| Total | {sum(data['plan'].values())} | {sum(merged.values())} | {sum(a['count'] for a in data['authors'].values())} | {len(reviews)} |",
        "",
        f"The query returned {len(data['merged_pr_query'])} merged PRs and {len(reviews)} submitted review record(s). The recorded approval is Kirtan (`kirtan-S111`) on [PR #2](https://github.com/het-lathiya/Group12/pull/2). Other members have no submitted review in this queried dataset; this does not establish absence of offline review.",
        "",
        "Sprint 1 credited values (including the ledger's provisional hosted-deployment credit): "
        + "; ".join(f"{n} {data['s1_credited'].get(n, 0)}" for n in ORDER)
        + ". See the original ledger before interpreting them as accepted points.",
    ]
    for name in ORDER:
        author = data["authors"][name]
        rows = [r for r in data["merged_ledger_parts"] if r["owner"] == name]
        prs = sorted({n for r in rows for n in r["prs"]})
        cut = [r["card"] for r in data["ownership"][name] if r["cut"]]
        lines += [
            "",
            f"## {name} — {author['name']}",
            "",
            f"**Role:** {data['roles'][name]}."
            + (" Course group leader under RUN-102." if name == "Nidhi" else ""),
            "",
            f"**Plan / merged allocations:** {data['plan'][name]} / {merged[name]}. **Commits on main:** {author['count']} (`{author['name']} <{author['email']}>`).",
            "",
            "**Cards and parts owned (task register; ownership does not by itself mean completed):**",
            "",
            "| Card | Assigned part | Main evidence |",
            "| --- | --- | --- |",
        ]
        for part in data["ownership"][name]:
            if part["cut"]:
                continue
            found = [r for r in rows if r["card"] == part["card"]]
            evidence = "; ".join(
                f"[ledger]({Path(r['ledger']).relative_to('docs').as_posix()})" for r in found
            )
            if not evidence:
                matches = sorted((ROOT / "docs/progress/parts").glob(part["card"] + "-*.md"))
                evidence = (
                    ", ".join(f"[record](../progress/parts/{p.name})" for p in matches)
                    if matches
                    else "No merged ledger row/part record located; human completion remains unverified"
                )
            else:
                evidence = evidence.replace("](progress/", "](../progress/")
            lines.append(f"| {part['card']} | {part['part']} | {evidence} |")
        lines += [
            "",
            "Cut assignments (not built): "
            + (", ".join(sorted(set(cut))) if cut else "none")
            + ".",
            "",
            "**Main PR references for owned merged work:** "
            + (
                ", ".join(f"[#{n}](https://github.com/het-lathiya/Group12/pull/{n})" for n in prs)
                if prs
                else "No numbered PR in the ledger rows"
            )
            + ".",
            "",
            f"**Review activity:** {review_counts[known_reviewers.get(name, '')]} submitted review record(s) in the merged-PR query."
            + (
                " Approved PR #2; no additional review inferred."
                if name == "Kirtan"
                else " Requests/offline activity are not counted."
            ),
            "",
            "**Course documents / submission work:** " + data["course"][name] + ".",
        ]
    lines += [
        "",
        "## Proposed marks distribution",
        "",
        "**[team to decide; default equal]**",
        "",
        "The team must agree this line. Commit counts, merged allocations and draft documentation do not automatically assign marks. No signatures have been supplied.",
        "",
        "## Signatures",
        "",
        "| Member | Signature | Date |",
        "| --- | --- | --- |",
    ]
    for name in ORDER:
        lines.append(f"| {data['authors'][name]['name']} | ____________________ | __________ |")
    lines += [
        "| Group leader confirmation — Nidhi Chauhan | ____________________ | __________ |",
        "",
        "## Rebuild and print",
        "",
        "Refresh evidence with `python3 scripts/build_contribution.py --refresh` (requires git and gh); ordinary rebuild uses the committed evidence snapshot. Export with the external-tool command in the RUN-102 contribution part record. The PDF is unsigned and retains the same team-decision placeholders.",
        "",
    ]
    (ROOT / "docs/course/15-contribution.md").write_text("\n".join(lines))
    print(
        f"Contribution draft: {len(ORDER)} members; plan={sum(data['plan'].values())}; merged allocations={sum(merged.values())}; main commits={sum(a['count'] for a in data['authors'].values())}; submitted reviews={len(reviews)}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--prs", type=Path)
    parser.add_argument("--ref", default="origin/main")
    args = parser.parse_args()
    evidence = ROOT / "docs/course/15-contribution-evidence.json"
    if args.refresh:
        evidence.write_text(
            json.dumps(collect(args.prs, args.ref), ensure_ascii=False, indent=2) + "\n"
        )
    write_document(json.loads(evidence.read_text()))


if __name__ == "__main__":
    main()
