"""Publication-safety static audit of the public candidate tree.

This test inspects ONLY the public candidate files (everything outside `internal/`,
`review-packages/`, `vendor/`, `.venv`, `.git`). It mirrors the checklist of the P0/P0-R1
sensitive-data scan and must pass before any release is even proposed.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    "internal",
    "review-packages",
    "vendor",
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
}

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
]

# Built dynamically so the detector literals do not self-match in these very test files.
ABS_PATH_MARKERS = ("/" + "home/", "/" + "Users/", "/m" + "nt/c/")


def _public_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for root in sorted(p for p in REPO.iterdir() if p.is_dir()):
        if root.name in EXCLUDED_DIRS:
            continue
        for p in root.rglob("*"):
            if p.is_file() and not any(part in EXCLUDED_DIRS for part in p.parts):
                out.append(p)
    for name in sorted(p.name for p in REPO.iterdir() if p.is_file()):
        if name not in ("README.md", "pyproject.toml", "uv.lock", ".python-version", ".gitignore",
                        "LICENSE", "CITATION.cff", "NOTICE.md", "THIRD_PARTY.md"):
            continue
        out.append(REPO / name)
    return out


def test_no_secrets_in_public_tree():
    problems: list[str] = []
    for p in _public_files():
        if p.suffix in {".png", ".pdf", ".gif", ".ipynb"}:
            continue
        try:
            text = p.read_bytes()
        except OSError:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text.decode("utf-8", errors="ignore")):
                problems.append(f"{p}: matched {pat.pattern}")
    assert not problems, "\n".join(problems)


def test_no_absolute_personal_paths_in_public_tree():
    problems: list[str] = []
    for p in _public_files():
        if p.suffix in {".png", ".pdf", ".gif"}:
            continue
        try:
            text = p.read_text()
        except OSError:
            continue
        for marker in ABS_PATH_MARKERS:
            if marker in text:
                problems.append(f"{p}: contains {marker}")
    assert not problems, "\n".join(problems)


def test_no_archives_or_cache_artifacts():
    problems = [str(p) for p in _public_files()
                if p.suffix in {".zip", ".gz", ".tar", ".pyc"} or p.name.endswith(":Zone.Identifier")]
    assert not problems, f"archive/cache artifact in public tree: {problems}"


def test_no_virtualenv_or_lockfile_leak():
    for p in _public_files():
        assert not p.name.startswith(".venv"), p
        assert p.name != "pyvenv.cfg", p


def test_public_tree_contains_no_review_zip_names():
    names = {p.name for p in _public_files()}
    assert not any("_REVIEW.zip" in n or "REVIEW.zip" in n for n in names)


def test_internal_and_review_dirs_are_ignored_by_gitignore():
    text = (REPO / ".gitignore").read_text()
    assert "review-packages/" in text
    assert "internal/" in text


def test_vendor_official_is_ignored():
    text = (REPO / ".gitignore").read_text()
    assert ("vendor/official/" in text) or ("vendor/" in text)