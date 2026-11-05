"""Frozen A3 source-integrity and bundling-policy tests."""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A3_DIR = REPO / "src" / "routing_study" / "a3"

FROZEN_FILES = ["solution.py", "placement.py", "routing.py"]

# Third-party solver sources that must never be bundled (link-only).
# (relative path normalized; hashes pinned in P0 records)
THIRD_PARTY_SOLVERS = {
    "computing/solver.py": "88d1babc1a8594236361509d30ed4b167a9da496a5551a2cdc0dc9057ca97049",  # HorizonRoute
    "solution/solve.py": "2d775edcfaeb5e2d8f465a7ac6a872d99d92df7c2beb292207d2499281b40c65",  # Exact-Beam
}

# Files whose presence is forbidden in the public candidate tree.
FORBIDDEN_NAMES = {
    "fusion_solver.py",  # F0 transcription of Exact-Beam orchestration (BLOCK)
}


def _sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _public_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for root in ("src", "tests", "scripts", "results", "docs"):
        base = REPO / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                out.append(p)
    for name in ("README.md", "NOTICE.md", "THIRD_PARTY.md", "CITATION.cff",
                 "pyproject.toml", "uv.lock", ".gitignore", ".python-version"):
        p = REPO / name
        if p.exists():
            out.append(p)
    return out


def test_frozen_a3_files_match_pinned_hashes():
    pin = json.loads((A3_DIR / "_frozen_hashes.json").read_text())["files"]
    for name in FROZEN_FILES:
        actual = _sha256(A3_DIR / name)
        expected = pin[name]
        assert actual == expected, f"{name} hash mismatch: {actual} != {expected}"


def test_frozen_a3_arch_lock_present():
    meta = json.loads((A3_DIR / "_frozen_hashes.json").read_text())
    assert meta["architecture_id"] == "OC-V2-A3-BIDIRECTIONAL-20260921"
    assert meta["status"].startswith("MIGRATED_BYTE_FOR_BYTE")


def test_no_third_party_solver_bundled():
    for p in _public_files():
        h = _sha256(p)
        for _, banned in THIRD_PARTY_SOLVERS.items():
            assert h != banned, f"banned third-party solver source appears at {p}"
        if p.name in FORBIDDEN_NAMES:
            pytest.fail(f"forbidden file present in public tree: {p}")


def test_no_f0_transcription():
    hits = [str(p) for p in _public_files() if p.name == "fusion_solver.py"]
    assert not hits, f"F0 transcription present: {hits}"


def test_frozen_files_not_rewritten_with_wrappers():
    """The frozen files must contain no package-relative imports beyond the original top-level ones."""
    for name in FROZEN_FILES:
        text = (A3_DIR / name).read_text()
        assert "routing_study" not in text, f"{name} references package layout (would imply rewrite)"


def test_public_tree_contains_no_pyc_or_pycache():
    for p in _public_files():
        assert p.suffix != ".pyc", f"pyc present in public tree: {p}"
        assert "__pycache__" not in p.parts, f"cache dir present in public tree: {p}"