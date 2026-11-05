"""Documentation & result-consistency checks (P2; hardened in P2-R1).

The contract tested here:

1. **Links & anchors.** Every internal Markdown link must resolve to an existing file **and**, when it
   carries a ``#anchor`` fragment, that anchor must actually exist as a GitHub-style heading slug in
   the target file (or in the same document when no path is given).
2. **Row-level numeric claims.** The headline results are verified **per table row**: the value claimed
   for a method must appear in that method's own row of the README results table, and a row must never
   carry another method's recorded total (cross-method mix detection).
3. **Negative controls.** The pure checker functions are exercised on deliberately wrong inputs to
   prove they actually detect broken anchors and swapped/incorrect scores.
4. **Command / CI hygiene.** Documented commands must correspond to files that exist; the optional CI
   workflow (if present) must be read-only, secret-free, and offline-only.
"""

from __future__ import annotations

import csv
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
DOCS = [REPO / "README.md", *(REPO / "docs").glob("*.md")]
LINK_RE = re.compile(r"\[[^]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_NON_WORD = re.compile(r"[^\w\- ]")
_SPACE = re.compile(r"\s+")


def github_slug(text: str) -> str:
    """GitHub-style anchor slug for an ATX heading."""
    return _SPACE.sub("-", _NON_WORD.sub("", text.lower()).strip()).strip("-")


def collect_heading_slugs(md_text: str) -> set[str]:
    slugs: set[str] = set()
    for line in md_text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            slugs.add(github_slug(m.group(1)))
    return slugs


def _display(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def check_internal_links(doc: pathlib.Path) -> list[str]:
    """Return violations: unresolvable internal files and/or missing #anchors."""
    text = doc.read_text()
    self_slugs = collect_heading_slugs(text)
    violations: list[str] = []
    for m in LINK_RE.finditer(text):
        raw = m.group(1).strip()
        if raw.startswith(("http://", "https://", "mailto:")) or raw.startswith("www."):
            continue
        target_part, _, anchor = raw.partition("#")
        target_part = target_part.strip()
        if target_part:
            target = (doc.parent / target_part).resolve()
            if not target.exists():
                violations.append(f"{_display(doc)}: broken file link '{raw}'")
                continue
            if anchor:
                slugs = collect_heading_slugs(target.read_text())
                if anchor not in slugs:
                    violations.append(
                        f"{_display(doc)}: anchor '#{anchor}' not found in {_display(target)}")
        else:
            if anchor and anchor not in self_slugs:
                violations.append(f"{_display(doc)}: anchor '#{anchor}' not found in same document")
    return violations


def test_internal_markdown_links_and_anchors_resolve():
    violations: list[str] = []
    for doc in DOCS:
        violations.extend(check_internal_links(doc))
    assert not violations, "broken links/anchors:\n" + "\n".join(violations)


# ------------------------------------------------------------------ row-level claims

def parse_table_rows(md_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in md_text.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            rows.append(cells)
    return rows


def normalize_cell(cell: str) -> str:
    """Strip markdown emphasis from a table cell: `**67.5 / 67.5**` -> `67.5 / 67.5`."""
    return cell.replace("**", "").replace("`", "").replace("_", "").strip()


# method token -> allowed recorded-total cell values (exact, normalized)
ROW_CLAIMS: dict[str, set[str]] = {
    "A3": {"110.0"},
    "HorizonRoute": {"68.5"},
    "Exact-Beam": {"67.5"},
    "F0 B0 / F1": {"67.5 / 67.5"},
    "F0 F2": {"68 / 69 / 68"},
}

# exact normalized cell -> owner method (used for cross-method mix detection)
KNOWN_VALUE_TO_OWNER: dict[str, str] = {
    "110.0": "A3", "68.5": "HorizonRoute", "67.5": "Exact-Beam",
    "67.5 / 67.5": "F0 B0 / F1", "68 / 69 / 68": "F0 F2",
}


def check_table_claims(md_text: str, claims: dict[str, set[str]]) -> list[str]:
    """Row-level consistency using **exact cell equality** (after markdown normalization).

    For every table row whose first cell mentions a known method:
    - the row must contain a cell exactly equal to one of that method's recorded totals;
    - no cell in the row may exactly equal another method's recorded total.
    """
    rows = parse_table_rows(md_text)
    violations: list[str] = []
    for cells in rows:
        if not cells:
            continue
        first = cells[0]
        for method, allowed in claims.items():
            if method.lower() not in first.lower():
                continue
            normalized_row = [normalize_cell(c) for c in cells]
            if not any(cell in allowed for cell in normalized_row):
                violations.append(
                    f"method '{method}' row lacks its recorded total (expected one of {sorted(allowed)})")
            for cell in normalized_row:
                owner = KNOWN_VALUE_TO_OWNER.get(cell)
                if owner is not None and owner != method:
                    violations.append(
                        f"method '{method}' row contains '{cell}' (a recorded total of '{owner}')")
    return violations


def test_readme_headline_numbers_match_csv_row_by_row():
    csv_totals = _csv_heads()
    # the README claims must equal the CSV-recorded totals for the corresponding method
    expected = {
        "A3": {f"{csv_totals['A3']:.1f}"},
        "HorizonRoute": {f"{csv_totals['HR']:.1f}"},
        "Exact-Beam": {f"{csv_totals['EB']:.1f}"},
        "F0 B0 / F1": {"67.5 / 67.5"},
        "F0 F2": {"68 / 69 / 68"},
    }
    text = (REPO / "README.md").read_text()
    violations = check_table_claims(text, expected)
    assert not violations, "\n".join(violations)


def _csv_heads() -> dict[str, float]:
    def rows(rel):
        with (REPO / "results" / rel).open(newline="") as fh:
            return list(csv.DictReader(fh))

    a3 = [r for r in rows("a3_historical.csv") if r["benchmark"].upper() == "TOTAL"][0]
    hr = [r for r in rows("horizonroute_reproduction.csv") if r["benchmark"].upper() == "TOTAL"][0]
    eb = [r for r in rows("exact_beam_reproduction.csv") if r["benchmark"].upper() == "TOTAL"][0]
    return {"A3": float(a3["score"]), "HR": float(hr["score"]), "EB": float(eb["score"])}


# ------------------------------------------------------------------ negative controls

def test_negative_control_wrong_score_detected():
    bad = "| Method | Total |\n|---|---|\n| HorizonRoute | **99.9** |\n| A3 | **110.0** |\n"
    violations = check_table_claims(bad, ROW_CLAIMS)
    assert any("lacks its recorded total" in v and "HorizonRoute" in v for v in violations), violations


def test_negative_control_cross_method_mix_detected():
    bad = "| Method | Total |\n|---|---|\n| A3 | **68.5** |\n| HorizonRoute | **68.5** |\n"
    violations = check_table_claims(bad, ROW_CLAIMS)
    assert any("contains '68.5'" in v and "A3'" in v for v in violations), violations


def test_negative_control_broken_anchor_detected(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("## Target\n\n[see](#missing-heading)\n")
    violations = check_internal_links(doc)
    assert any("missing-heading" in v for v in violations), violations


def test_negative_control_cross_file_missing_anchor_detected(tmp_path):
    other = tmp_path / "other.md"
    other.write_text("## Actual heading here\n")
    doc = tmp_path / "doc.md"
    doc.write_text(f"[x]({other.name}#wrong-anchor)\n")
    violations = check_internal_links(doc)
    assert any("wrong-anchor" in v for v in violations), violations


def test_negative_control_broken_file_link_detected(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("[x](missing-sibling.md)\n")
    violations = check_internal_links(doc)
    assert any("broken file link" in v for v in violations), violations


# ------------------------------------------------------------------ tags, commands, CI

def test_tags_and_status_consistent():
    text = "\n".join(d.read_text() for d in DOCS)
    for token in ("RECORDED_HISTORICAL", "LOCALLY_REPRODUCED_HISTORICAL", "EXPERIMENTAL_LOCAL",
                  "65.5", "26.5", "NOT_EVIDENCED", "NO_GO_FURTHER_RESEARCH"):
        assert token in text, f"required disclosure marker missing: {token}"


def test_commands_referenced_exist():
    text = "\n".join(d.read_text() for d in DOCS)
    for needle in ("uv sync --frozen", "uv run pytest", "scripts/fetch_official_starter.py",
                   "src/routing_study/a3/"):
        assert needle in text, f"documented command/path missing: {needle}"
    assert (REPO / "scripts" / "fetch_official_starter.py").is_file()
    assert (REPO / "src" / "routing_study" / "a3" / "solution.py").is_file()


def test_no_forbidden_head_to_head_language():
    text = "\n".join(d.read_text() for d in DOCS).lower()
    for phrase in ("beats horizonroute", "beats exact-beam", "outperforms horizonroute",
                   "outperforms exact-beam", "state of the art", "production-ready"):
        assert phrase not in text, f"overclaim phrasing found: {phrase}"


def test_ci_workflow_is_local_read_only_planning():
    wf_path = REPO / ".github" / "workflows" / "ci.yml"
    if not wf_path.is_file():
        pytest.skip("CI workflow not prepared")
    wf = yaml.safe_load(wf_path.read_text())
    perms = wf.get("permissions", {})
    assert perms.get("contents") == "read"
    raw = wf_path.read_text()
    flat = str(wf)
    for forbidden in ("${{ secrets.", "GH_TOKEN", "github-token:", "- name: Deploy", "- name: Publish"):
        assert forbidden not in flat and forbidden not in raw
    assert "run:" in raw
    assert "not external" in raw