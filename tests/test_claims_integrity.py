"""Scientific-claims hygiene tests for README, docs, and results tables."""

from __future__ import annotations

import csv
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]

TEXT_FILES = [
    "README.md",
    "NOTICE.md",
    "THIRD_PARTY.md",
    "docs/RESEARCH_REPORT.md",
    "docs/METHODOLOGY.md",
    "docs/LIMITATIONS.md",
    "docs/REPRODUCIBILITY.md",
    "docs/EVIDENCE_INDEX.md",
]

# Phrases that must NOT appear as claims (checked for the prohibited sense by exact-match scan).
FORBIDDEN_CLAIMS = [
    "quantum advantage",
    "quantum speedup",
    "globally optimal",
    "global optimality",
    "state of the art",
    "beats all",
    "outperforms all",
    "production-ready",
    "production readiness",
    "officially endorsed",
    "endorsed by Q-SITE",
]

REQUIRED_DISCLOSURES = [
    "RECORDED_HISTORICAL",
    "LOCALLY_REPRODUCED_HISTORICAL",
    "NOT_EVIDENCED",
    "NO_GO_FURTHER_RESEARCH",
    "budget",  # at least some budget discussion
    "20",  # the 20 s budget / deviation is discussed
    "26.5",  # stretch exclusion stated
]


def test_no_forbidden_claims_in_text_files():
    # Forbidden phrases are permitted only inside sections that contain an explicit negation /
    # disclaimer (e.g. "must never be cited to support", "no claim is made").
    negation = ("forbidden", "forbid", "no claim", "not a claim", "does not", "must not",
                "never", "without", "cannot be used to support", "excluded", "out of scope")
    for rel in TEXT_FILES:
        lines = (REPO / rel).read_text().splitlines()
        current_section = ""
        section_text = ""
        section_has_header = False
        for line in lines:
            if line.startswith("#"):
                if section_has_header:
                    _assert_section_clean(rel, current_section, section_text, negation)
                current_section = line
                section_text = ""
                section_has_header = True
            else:
                section_text += line + "\n"
        if section_has_header:
            _assert_section_clean(rel, current_section, section_text, negation)


def _assert_section_clean(rel, header, body, negation):
    lowered = body.lower()
    if not any(token in lowered for token in negation):
        for phrase in FORBIDDEN_CLAIMS:
            if phrase in lowered:
                assert False, f"forbidden claim '{phrase}' in a non-disclaiming section ({header}) of {rel}"


def test_required_disclosures_present_globally():
    blob = "\n".join((REPO / rel).read_text() for rel in TEXT_FILES).lower()
    for disp in REQUIRED_DISCLOSURES:
        assert disp.lower() in blob, f"missing required disclosure marker: {disp}"


def test_results_tables_carry_evidence_pointers():
    for rel in ["results/a3_historical.csv", "results/horizonroute_reproduction.csv",
                "results/exact_beam_reproduction.csv", "results/fusion_experiment.csv"]:
        rows = list(csv.DictReader((REPO / rel).open(newline="")))
        # every data row must name at least one evidence source
        for r in rows:
            evidence = (r.get("evidence") or "").strip()
            assert evidence, f"{rel}: row without evidence: {r}"


def test_a3_historical_is_not_relabeled_as_rerun():
    rows = list(csv.DictReader((REPO / "results/a3_historical.csv").open(newline="")))
    statuses = {r["status"] for r in rows if r["benchmark"].upper() != "TOTAL"}
    assert statuses == {"RECORDED_HISTORICAL"}


def test_fusion_target_negative_result_reported():
    rows = list(csv.DictReader((REPO / "results/fusion_experiment.csv").open(newline="")))
    notes = " ".join(r.get("notes") or "" for r in rows).lower()
    assert "65.5" in notes
    assert "not met" in notes


def test_third_party_scope_clear():
    tp = (REPO / "THIRD_PARTY.md").read_text().lower()
    assert ("not bundled" in tp) or ("never bundled" in tp)
    assert "link-by-commit" in tp
    assert "unlicensed" in tp
    assert "mihir talati" in tp


def test_no_personal_absolute_paths_in_docs():
    markers = ("/" + "home/", "/" + "Users/", "/m" + "nt/c/")
    for rel in TEXT_FILES:
        text = (REPO / rel).read_text()
        for marker in markers:
            assert marker not in text, f"absolute personal path in {rel}"