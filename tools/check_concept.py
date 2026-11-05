#!/usr/bin/env python3
"""Check that every number in CONCEPT.md is backed by its source.

Rule (stated in CONCEPT.md itself): every number in the running text and tables is followed, in the same
paragraph or table cell, by a tag in square brackets. The numbers a tag covers are those between it and the previous
tag (or the start of the paragraph / row). Tags:
  [FC-01], [WU-03; H2-02], ...  rows of RESULTS_INDEX.md: each covered number must equal, at its shown precision, one of
                                the numbers in that row's Value, N or "CI or range" cells (any of the listed rows)
  [spec]                        a design or protocol constant: the number must appear in docs/SPEC.md
  [prior art]                   a figure of a published work or a datasheet: it must appear in
                                results/wrapup/prior_art/PRIOR_ART.md
A number with no tag after it in its paragraph or cell is reported as untagged. Not counted as numbers: fenced code
blocks (diagrams), headings, list/section numbering, identifiers glued to letters (X80, row7, fitc10, v2.1, na1-5),
the release label v1.0, "§" references, and DOIs/arXiv IDs.
Usage: python3 tools/check_concept.py [--doc CONCEPT.md] [--json out.json]. Exit 0 only if everything matches.
The index rows themselves are checked against the summary files by tools/check_results_index.py."""
import json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import check_results_index as CRI   # noqa: E402  (parse_index, numbers, match)

TAG = re.compile(r"\[((?:[A-Z][A-Z0-9]*-\d+[a-z]?|spec|prior art)(?:\s*[;,]\s*(?:[A-Z][A-Z0-9]*-\d+[a-z]?|spec|prior art))*)\]")
STRIP = [r"\bv1\.0\b", r"§\s*\d+(?:\.\d+)*(?:\s*[–-]\s*\d+(?:\.\d+)*)?", r"\bDOI\s+\S+", r"\barXiv:\s*\S+",
         r"\b10\.\d{4,}/\S+", r"\b[Ss]tudy\s+\d\b", r"\b[Ss]ection\s+\d+\b", r"\b3B-[VP]\b", r"\bngspice-\d+", r"\bLevel-\d+", r"Wilson 95\s*%", r"\bVariant \d+", r"\blessons? \d+(?:\s*[,–-]\s*\d+)*", r"\b[A-Z]{1,3}\d+[\w.-]*", r"\(\d+\)\s"]


def segments(text):
    """Yield (line_no, segment_text) units: table rows and paragraphs, outside fenced code, comments and headings."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    lines = text.splitlines()
    in_code, para, start = False, [], 0
    for i, l in enumerate(lines, 1):
        if l.strip().startswith("```"):
            in_code = not in_code
            if para:
                yield start, " ".join(para); para = []
            continue
        if in_code:
            continue
        if l.startswith("#"):
            if para:
                yield start, " ".join(para); para = []
            continue
        if l.startswith("|"):
            if para:
                yield start, " ".join(para); para = []
            if set(l.replace("|", "").strip()) <= set("-: "):
                continue
            yield i, " ; ".join(re.split(r"(?<!\\)\|", l.strip()[1:-1]))   # a table row is one unit (tag in its last cell)
            continue
        if not l.strip():
            if para:
                yield start, " ".join(para); para = []
            continue
        if not para:
            start = i
        para.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l))
    if para:
        yield start, " ".join(para)


def clean(s):
    s = re.sub(r"`[^`]*`", " ", s)                     # inline code: file names, node names
    s = re.sub(r"\]\([^)]*\)", "] ", s)                 # link targets
    tags = []
    s = TAG.sub(lambda m: tags.append(m.group(0)) or f"\x00{len(tags) - 1}\x00", s)   # protect tags while stripping
    for p in STRIP:
        s = re.sub(p, " ", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: tags[int(m.group(1))], s)


def main():
    args = sys.argv[1:]
    doc = REPO / (args[args.index("--doc") + 1] if "--doc" in args else "CONCEPT.md")
    rows = CRI.parse_index(REPO / "RESULTS_INDEX.md")
    spec = (REPO / "docs/SPEC.md").read_text()
    pa = (REPO / "results/wrapup/prior_art/PRIOR_ART.md").read_text()
    spec_nums = CRI.numbers(spec.replace(" ", " "))
    pa_nums = CRI.numbers(pa)
    problems, n_checked, n_tags = [], 0, 0
    for ln, seg in segments(doc.read_text()):
        s = clean(seg)
        pos = 0
        for m in TAG.finditer(s):
            n_tags += 1
            chunk = s[pos:m.start()]
            pos = m.end()
            nums = CRI.numbers(chunk)
            ids = [t.strip() for t in re.split(r"[;,]", m.group(1))]
            pool = []
            for t in ids:
                if t == "spec":
                    pool += spec_nums
                elif t == "prior art":
                    pool += pa_nums
                elif t in rows:
                    for col in ("Quantity", "Value", "N", "CI or range"):
                        pool += CRI.numbers(rows[t].get(col, ""))
                else:
                    problems.append(dict(line=ln, problem=f"unknown tag [{t}]"))
            for v in nums:
                n_checked += 1
                if not any(CRI.match(v, p[0]) and (v[1] <= p[1] or v[2]) for p in pool):
                    problems.append(dict(line=ln, problem=f"{v[0]:g} not found in [{m.group(1)}]", text=chunk.strip()[-90:]))
        rest = CRI.numbers(s[pos:])
        for v in rest:
            problems.append(dict(line=ln, problem=f"untagged number {v[0]:g}", text=s[pos:].strip()[:90]))
    for p in problems:
        print(f"  FAIL line {p['line']}: {p['problem']}" + (f"   ...{p.get('text', '')}" if p.get("text") else ""))
    print(f"{n_checked} tagged numbers checked under {n_tags} tags; {len(problems)} problems")
    if "--json" in args:
        pathlib.Path(args[args.index("--json") + 1]).write_text(json.dumps(dict(checked=n_checked, tags=n_tags, problems=problems), indent=1))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
