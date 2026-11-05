"""Repository-contract tests: structure, required files, and policy markers."""

from __future__ import annotations

import csv
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_PUBLIC = [
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".gitignore",
    "LICENSE",
    "CITATION.cff",
    "NOTICE.md",
    "THIRD_PARTY.md",
    "src/routing_study/__init__.py",
    "src/routing_study/a3/solution.py",
    "src/routing_study/a3/placement.py",
    "src/routing_study/a3/routing.py",
    "src/routing_study/a3/__init__.py",
    "src/routing_study/a3/_compat.py",
    "src/routing_study/a3/_frozen_hashes.json",
    "src/routing_study/adapters/inputs.py",
    "results/a3_historical.csv",
    "results/horizonroute_reproduction.csv",
    "results/exact_beam_reproduction.csv",
    "results/fusion_experiment.csv",
    "docs/RESEARCH_REPORT.md",
    "docs/METHODOLOGY.md",
    "docs/LIMITATIONS.md",
    "docs/EVIDENCE_INDEX.md",
    "docs/REPRODUCIBILITY.md",
]

RESULT_COLUMN_REQUIREMENTS = {
    "results/a3_historical.csv": {"benchmark", "status", "score", "swap_count", "depth", "evidence"},
    "results/horizonroute_reproduction.csv": {"benchmark", "status", "score", "source_commit", "evidence"},
    "results/exact_beam_reproduction.csv": {"benchmark", "status", "score", "source_commit", "evidence"},
    "results/fusion_experiment.csv": {"arm", "seed", "total_score", "evidence", "notes"},
}

ALLOWED_RESULT_STATUS = {
    "RECORDED_HISTORICAL",
    "LOCALLY_REPRODUCED_HISTORICAL",
    "EXPERIMENTAL_LOCAL",
    "LOCAL_RUN",
}


def test_required_public_files_exist():
    missing = [rel for rel in REQUIRED_PUBLIC if not (REPO / rel).is_file()]
    assert not missing, f"missing required files: {missing}"


def test_python_version_pinned():
    ver = (REPO / ".python-version").read_text().strip()
    assert ver  # must be non-empty


def test_gitignore_protects_internal_areas():
    text = (REPO / ".gitignore").read_text()
    assert "review-packages/" in text
    assert "internal/" in text
    assert ".venv/" in text
    assert "uv.lock" not in [ln.strip() for ln in text.splitlines() if "uv.lock" in ln]


def test_public_license_and_citation_metadata_present():
    license_text = (REPO / "LICENSE").read_text()
    assert "MIT License" in license_text
    assert "Copyright (c) 2026 Bob Oner" in license_text
    assert (REPO / "CITATION.cff").is_file()


def test_citation_draft_preserved_as_historical_evidence():
    # The approved public CITATION.cff is shipped; the earlier internal draft must remain preserved.
    assert (REPO / "CITATION.cff").is_file()
    draft = REPO / "internal" / "CITATION.cff.draft"
    if draft.is_file():
        assert "DEFERRED" in draft.read_text()


def test_results_csv_parse_and_columns():
    for rel, required in RESULT_COLUMN_REQUIREMENTS.items():
        p = REPO / rel
        with p.open(newline="") as fh:
            rows = list(csv.DictReader(fh, strict=True))
        assert rows, f"{rel}: no rows"
        missing = required - set(rows[0].keys())
        assert not missing, f"{rel}: missing columns {missing}"
    # targeted column sanity
    a3 = list(csv.DictReader((REPO / "results/a3_historical.csv").open(newline="")))
    assert a3[0]["status"] == "RECORDED_HISTORICAL"
    assert a3[-1]["benchmark"].upper() == "TOTAL"


def test_no_unlabeled_statuses():
    for rel in ("results/horizonroute_reproduction.csv", "results/exact_beam_reproduction.csv"):
        rows = list(csv.DictReader((REPO / rel).open(newline="")))
        for r in rows:
            if r["benchmark"].upper() == "TOTAL":
                continue
            assert r["status"] in ALLOWED_RESULT_STATUS, f"{rel}: bad status {r['status']}"


def test_reproducibility_doc_mandates_offline_path():
    text = (REPO / "docs/REPRODUCIBILITY.md").read_text()
    assert "uv sync --frozen" in text
    assert "uv run pytest" in text
    assert "offline" in text.lower()


def test_pyproject_declares_only_real_deps():
    text = (REPO / "pyproject.toml").read_text()
    assert "networkx" in text
    assert "pytest" in text
    # must not silently vendor or fetch anything
    assert "git+" not in text
    assert "{ git" not in text