#!/usr/bin/env python3
"""Build a sanitized public-candidate snapshot with an explicit, fail-closed allowlist (P3-CI-R1).

This helper produces a *public-source-only* copy of the candidate tree for review packages.

Security contract (P3-CI-R1 hardening):

- R1 **Refuse symbolic links.** Every filesystem object is inspected with ``lstat`` (the link
  itself is the authority — nothing is followed). Symlinked files and symlinked directories anywhere
  under an allowed top-level entry cause the build to FAIL.
- R2 **Refuse hardlinked source files.** A regular file whose link count ``st_nlink > 1`` is
  rejected (it might alias content outside the repository).
- R3 **Refuse special objects.** Only regular files (``S_ISREG``) and real directories
  (``S_ISDIR``) are admissible; devices, sockets, FIFOs and other special objects cause FAIL.
- R4 **Exact relative-path admission.** ``EXACT_ALLOWLIST`` is the authoritative set of public source
  files. Any regular file under an allowed top-level entry that is NOT in the allowlist is
  "unapproved" and FAILS the build (no silent inclusion). Runtime caches (``__pycache__/*.pyc``,
  ``.pytest_cache``, ``.git``, ``.venv*``) are excluded without failing. Future additions (e.g.
  LICENSE/CITATION.txt for P3-META) require an explicit allowlist update and separate admission.
- R5 **Fail-closed preflight.** All sources are validated BEFORE anything is copied; a rejected build
  leaves the destination untouched/absent. Mid-copy failures remove the destination (created this run).
- R6 **Deterministic inventories.** ``public_source_inventory.txt`` and ``SHA256SUMS.txt`` are emitted
  in sorted allowlist order.
- R7 **Source read-only.** The helper only reads the source repository; it never writes there.

Usage:
    uv run python scripts/make_candidate_snapshot.py --dest /tmp/p3snapshot
    uv run python scripts/make_candidate_snapshot.py --repo /tmp/synth --dest /tmp/out   # tests
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import stat
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

# Exact public-source admission list (relative to the repository root).
# 41 files from the P3-META gate: the previous 39 baseline plus LICENSE and CITATION.cff.
# Any further change requires explicit re-admission.
EXACT_ALLOWLIST = frozenset({
    ".github/workflows/ci.yml",
    ".gitignore",
    ".python-version",
    "CITATION.cff",
    "LICENSE",
    "NOTICE.md",
    "README.md",
    "THIRD_PARTY.md",
    "docs/EVIDENCE_INDEX.md",
    "docs/LIMITATIONS.md",
    "docs/METHODOLOGY.md",
    "docs/REPRODUCIBILITY.md",
    "docs/RESEARCH_REPORT.md",
    "pyproject.toml",
    "results/a3_historical.csv",
    "results/exact_beam_reproduction.csv",
    "results/fusion_experiment.csv",
    "results/horizonroute_reproduction.csv",
    "scripts/fetch_official_starter.py",
    "scripts/make_candidate_snapshot.py",
    "src/routing_study/__init__.py",
    "src/routing_study/a3/__init__.py",
    "src/routing_study/a3/_compat.py",
    "src/routing_study/a3/_frozen_hashes.json",
    "src/routing_study/a3/placement.py",
    "src/routing_study/a3/routing.py",
    "src/routing_study/a3/solution.py",
    "src/routing_study/adapters/__init__.py",
    "src/routing_study/adapters/inputs.py",
    "tests/test_a3_import.py",
    "tests/test_a3_integrity.py",
    "tests/test_a3_official_scorer_optional.py",
    "tests/test_a3_smoke.py",
    "tests/test_claims_integrity.py",
    "tests/test_docs_and_results_consistency.py",
    "tests/test_fetch_official_starter_safety.py",
    "tests/test_metadata_validation.py",
    "tests/test_public_tree_hygiene.py",
    "tests/test_publication_safety.py",
    "tests/test_repository_contract.py",
    "uv.lock",
})

CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", ".venv"}


def _top_level() -> list[str]:
    return sorted({rel.split("/", 1)[0] for rel in EXACT_ALLOWLIST})


def _is_runtime_cache(rel: pathlib.Path) -> bool:
    if rel.suffix == ".pyc":
        return True
    return any(part in CACHE_DIR_NAMES or part.startswith("venv-") for part in rel.parts)


def classify(repo: pathlib.Path, rel: pathlib.Path) -> str:
    """Return 'ok' or a problem kind describing the object at repo/rel (authoritative=lstat)."""
    try:
        st = (repo / rel).lstat()
    except FileNotFoundError:
        return "missing"
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if not stat.S_ISREG(st.st_mode):
        return "special"
    if st.st_nlink > 1:
        return "hardlink"
    return "ok"


def preflight(repo: pathlib.Path, allowlist: frozenset[str]) -> tuple[set[str], list[tuple[str, str]]]:
    """Validate the whole source before copying. Returns (admitted_rel_paths, problems)."""
    problems: list[tuple[str, str]] = []
    admitted: set[str] = set()

    def visit(rel: pathlib.Path) -> None:
        kind = classify(repo, rel)
        if kind == "missing":
            problems.append(("missing", str(rel)))
            return
        if kind == "symlink":
            problems.append(("symlink", str(rel)))
            return
        if kind == "special":
            problems.append(("special", str(rel)))
            return
        if kind == "hardlink":
            problems.append(("hardlink", str(rel)))
            return
        if kind == "dir":
            if _is_runtime_cache(rel):
                return
            for child in sorted((repo / rel).iterdir()):
                visit(rel / child.name)
            return
        # regular, single-link file (classify returns "ok")
        if _is_runtime_cache(rel):
            return
        key = str(rel)
        if key not in allowlist:
            problems.append(("unapproved", key))
            return
        admitted.add(key)

    for top in _top_level():
        visit(pathlib.Path(top))

    # every allowlisted file must have been visited and admitted
    for rel in sorted(allowlist):
        if rel not in admitted:
            problems.append(("missing-admitted", rel))
    return admitted, problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a sanitized public-candidate snapshot (fail-closed).")
    ap.add_argument("--dest", required=True, help="destination directory (must be outside the source repo)")
    ap.add_argument("--repo", default=None, help="source repository root (default: this repository)")
    ap.add_argument("--allowlist-file", default=None, help="override allowlist (line-separated relative paths)")
    args = ap.parse_args()

    repo = pathlib.Path(args.repo).expanduser().resolve() if args.repo else REPO
    dest = pathlib.Path(args.dest).expanduser().resolve()

    try:
        dest.relative_to(repo)
    except ValueError:
        pass
    else:
        print(f"[ERROR] destination must be outside the source repository: {dest}", file=sys.stderr)
        return 2

    allowlist = EXACT_ALLOWLIST
    if args.allowlist_file:
        with open(args.allowlist_file) as fh:
            allowlist = frozenset(ln.strip() for ln in fh if ln.strip())

    admitted, problems = preflight(repo, allowlist)
    if problems:
        print("[FAIL] preflight rejected snapshot sources:", file=sys.stderr)
        for kind, rel in sorted(problems):
            print(f"  [{kind}] {rel}", file=sys.stderr)
        return 4

    if dest.exists() and any(dest.iterdir()):
        print(f"[ERROR] destination not empty; refusing to overwrite: {dest}", file=sys.stderr)
        return 3
    dest.mkdir(parents=True, exist_ok=True)

    ordered = sorted(admitted)
    try:
        for rel in ordered:
            src = repo / rel
            tgt = dest / rel
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tgt)
    except Exception as exc:  # noqa: BLE001 -- fail-closed cleanup
        shutil.rmtree(dest, ignore_errors=True)
        print(f"[ERROR] copy failed; destination removed: {exc}", file=sys.stderr)
        return 5

    with (dest / "public_source_inventory.txt").open("w") as fh:
        for rel in ordered:
            fh.write(rel + "\n")
    with (dest / "SHA256SUMS.txt").open("w") as fh:
        for rel in ordered:
            fh.write(f"{hashlib.sha256((dest / rel).read_bytes()).hexdigest()}  {rel}\n")

    print(f"snapshot written to {dest}: {len(ordered)} source files (allowlist-admitted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())