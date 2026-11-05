"""Public-tree hygiene + snapshot security tests (P3-CI, hardened in P3-CI-R1).

Two distinct concepts are kept apart:
- **public source inventory** — the source files of the sanitized public candidate (produced by
  ``scripts/make_candidate_snapshot.py`` from its exact relative-path allowlist);
- **post-execution cache inventory** — ``__pycache__/*.pyc`` (and ``.venv``) created at *runtime* by
  imports/tests; git-ignored and never part of any snapshot.

Security contract exercised here (P3-CI-R1):

- R1 symlinked files/dirs are refused (filesystem object inspected via ``lstat``, nothing followed);
- R2 source files with link count > 1 (hardlinks into external content) are refused;
- R3 non-regular filesystem objects are refused;
- R4 only the exact allowlisted relative paths are admitted; any new unapproved file under an allowed
  directory aborts the build;
- R5 preflight runs before any copy; a rejected build leaves the destination absent/empty;
- R6 inventories and hashes are deterministic;
- R7 the source repository is only ever read.

Mandatory negative controls N1-N8 are executed below with **synthetic content only** (isolated
``tmp_path``). The real repository is only used read-only by the baseline-equality test (N8).
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "make_candidate_snapshot.py"

ALLOWED_ACTIONS = {"actions/checkout", "astral-sh/setup-uv"}


def module():
    spec = importlib.util.spec_from_file_location("make_candidate_snapshot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_snapshot(dest: pathlib.Path, repo: pathlib.Path | None = None,
                    allowlist_file: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "--dest", str(dest)]
    if repo is not None:
        cmd += ["--repo", str(repo)]
    if allowlist_file is not None:
        cmd += ["--allowlist-file", str(allowlist_file)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def materialize(repo: pathlib.Path, rels) -> None:
    """Create a synthetic source tree containing the given relative files."""
    for rel in rels:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# synthetic content for {rel}\n")


# ------------------------------------------------------------------ baseline / allowed set

def test_baseline_allowlist_is_exact_and_stable():
    mod = module()
    allow = mod.EXACT_ALLOWLIST
    assert len(allow) == 41, f"baseline public allowlist changed: {len(allow)} files"
    assert "LICENSE" in allow and "CITATION.cff" in allow
    assert "src/routing_study/a3/solution.py" in allow
    assert "results/a3_historical.csv" in allow
    for rel in allow:
        assert "internal/" not in rel and "review-packages/" not in rel and "vendor/" not in rel


def _synthetic_repo(tmp_path: pathlib.Path, allow) -> pathlib.Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    materialize(repo, allow)
    return repo


# ------------------------------------------------------------------ N1..N5 fail-closed negatives

def _assert_rejected(proc: subprocess.CompletedProcess, dest: pathlib.Path, needle: str):
    assert proc.returncode != 0, f"expected rejection, got rc=0:\n{proc.stdout}\n{proc.stderr}"
    assert needle in (proc.stdout + proc.stderr), f"missing marker '{needle}' in: {proc.stdout} {proc.stderr}"
    assert not dest.exists(), "rejected build must not leave a destination"


def test_n1_symlink_to_external_file_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    external = tmp_path / "external-secret.txt"
    external.write_text("synthetic external secret")
    (repo / "docs" / "leak.md").symlink_to(external)
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "symlink")
    assert proc.returncode == 4


def test_n1b_symlink_dir_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    external_dir = tmp_path / "external-dir"
    external_dir.mkdir()
    (external_dir / "src").mkdir(parents=True)
    (external_dir / "src" / "x.py").write_text("SENSITIVE")
    (repo / "src").rename(repo / "src.orig")
    (repo / "src").symlink_to(external_dir / "src", target_is_directory=True)
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "symlink")
    assert (external_dir / "src" / "x.py").read_text() == "SENSITIVE"  # untouched


def test_n2_hardlink_to_external_file_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    external = tmp_path / "external-hard.txt"
    external.write_text("synthetic external hardlink secret")
    target = repo / "docs" / "leak_hard.md"
    os.link(external, target)  # nlink == 2 per inode shared with external
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "hardlink")


def test_n3_unapproved_file_under_docs_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    (repo / "docs" / "unapproved.md").write_text("new file not in allowlist")
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "unapproved")
    assert "docs/unapproved.md" in proc.stderr


def test_n4_unapproved_file_under_scripts_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    (repo / "scripts" / "secret_adder.py").write_text("new file not in allowlist")
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "unapproved")
    assert "scripts/secret_adder.py" in proc.stderr


def test_n5_credential_like_file_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    (repo / "src" / "routing_study" / "credentials.env").write_text(
        "PLACEHOLDER_TOKEN=synthetic-not-real\n")
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest, repo)
    _assert_rejected(proc, dest, "unapproved")
    assert "credentials.env" in proc.stderr
    assert "synthetic-not-real" not in (dest.read_bytes().decode() if dest.exists() else "")


# ------------------------------------------------------------------ N6/N7 destination guards

def test_n6_destination_inside_source_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    dest = repo / "vendor" / "snap"   # inside the source repository
    proc = _build_snapshot(dest, repo)
    assert proc.returncode == 2
    assert "outside the source repository" in proc.stderr


def test_n7_nonempty_destination_rejected(tmp_path):
    allow = module().EXACT_ALLOWLIST
    repo = _synthetic_repo(tmp_path, allow)
    dest = tmp_path / "snap"
    dest.mkdir()
    (dest / "existing.txt").write_text("keep")
    proc = _build_snapshot(dest, repo)
    assert proc.returncode == 3
    assert (dest / "existing.txt").read_text() == "keep"


# ------------------------------------------------------------------ N8 baseline equality + R6 determinism

def test_n8_baseline_produces_exact_inventory_and_is_deterministic(tmp_path):
    allow = module().EXACT_ALLOWLIST
    dest1, dest2 = tmp_path / "snap1", tmp_path / "snap2"
    proc = _build_snapshot(dest1)   # real repository, read-only
    assert proc.returncode == 0, proc.stdout + proc.stderr
    inv1 = set((dest1 / "public_source_inventory.txt").read_text().splitlines())
    assert inv1 == allow, f"inventory != exact allowlist: {(allow - inv1)} vs {(inv1 - allow)}"
    assert _build_snapshot(dest2).returncode == 0
    assert (dest1 / "SHA256SUMS.txt").read_text() == (dest2 / "SHA256SUMS.txt").read_text(), \
        "snapshot hashes must be deterministic"


def test_snapshot_includes_license_and_citation_with_matching_shas(tmp_path):
    dest = tmp_path / "snap"
    assert _build_snapshot(dest).returncode == 0
    inv = (dest / "public_source_inventory.txt").read_text().splitlines()
    assert "LICENSE" in inv and "CITATION.cff" in inv
    sums = dict(line.split("  ", 1)[::-1] for line in
                (dest / "SHA256SUMS.txt").read_text().splitlines())
    import hashlib as _h

    for rel in ("LICENSE", "CITATION.cff"):
        assert _h.sha256((REPO / rel).read_bytes()).hexdigest() == sums[rel]
        assert _h.sha256((dest / rel).read_bytes()).hexdigest() == sums[rel]


def test_snapshot_total_is_41_plus_inventory_files(tmp_path):
    dest = tmp_path / "snap"
    assert _build_snapshot(dest).returncode == 0
    inv = (dest / "public_source_inventory.txt").read_text().splitlines()
    assert len(inv) == 41, f"expected 41 admitted source files, got {len(inv)}"
    all_files = [p for p in dest.rglob("*") if p.is_file()]
    # 41 source files + public_source_inventory.txt + SHA256SUMS.txt = 43
    assert len(all_files) == 43, f"expected 43 total snapshot files, got {len(all_files)}"
    assert (dest / "public_source_inventory.txt").is_file()
    assert (dest / "SHA256SUMS.txt").is_file()


# ------------------------------------------------------------------ positive: real snapshot hygiene

def test_snapshot_contains_no_runtime_or_internal_artifacts(tmp_path):
    dest = tmp_path / "snap"
    proc = _build_snapshot(dest)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    forbidden_suffixes = {".pyc"}
    forbidden_names = {"__pycache__", ".venv", "internal", "review-packages", "vendor"}
    hits = [str(p) for p in dest.rglob("*")
            if p.suffix in forbidden_suffixes
            or p.name in forbidden_names
            or ".venv" in p.parts
            or "__pycache__" in p.parts]
    assert not hits, f"runtime/internal artifacts leaked into snapshot: {hits}"


def test_snapshot_contains_no_local_machine_paths(tmp_path):
    dest = tmp_path / "snap"
    assert _build_snapshot(dest).returncode == 0
    markers = (b"/" + b"home/", b"/" + b"Users/", b"/m" + b"nt/c/")
    for p in dest.rglob("*"):
        if not p.is_file():
            continue
        blob = p.read_bytes().lower()
        for marker in markers:
            assert marker not in blob, f"local machine path leaked into snapshot: {p.relative_to(dest)}"


def test_snapshot_guard_refuses_in_repo_dest(tmp_path):
    proc = _build_snapshot(REPO / "vendor" / "snap")
    assert proc.returncode == 2
    assert "outside the source repository" in proc.stderr


def test_gitignore_covers_runtime_cache_artifacts():
    text = (REPO / ".gitignore").read_text()
    for token in ("__pycache__/", "*.py[cod]", ".venv/", "internal/", "review-packages/", "vendor/"):
        assert token in text, f".gitignore missing {token}"


def test_workflow_uses_full_length_pinned_shas():
    wf = REPO / ".github" / "workflows" / "ci.yml"
    if not wf.is_file():
        pytest.skip("workflow not prepared")
    import re

    for m in re.finditer(r"uses:\s*([^\s]+)@([0-9a-f]{40})", wf.read_text()):
        assert m.group(1) in ALLOWED_ACTIONS
        assert len(m.group(2)) == 40
    for m in re.finditer(r"uses:\s*([^\s]+)@([^\s]+)", wf.read_text()):
        assert len(m.group(2)) == 40, f"action not pinned to full SHA: {m.group(0)}"


def test_no_secrets_or_deploy_in_workflow():
    wf_path = REPO / ".github" / "workflows" / "ci.yml"
    if not wf_path.is_file():
        pytest.skip("workflow not prepared")
    import yaml

    wf = yaml.safe_load(wf_path.read_text())
    assert wf.get("permissions", {}).get("contents") == "read"
    lines = [ln for ln in wf_path.read_text().splitlines() if not ln.strip().startswith("#")]
    raw = "\n".join(lines).lower()
    for forbidden in ("${{ secrets.", "gh_token", "github-token:", "artifact", "deploy", "publish"):
        assert forbidden not in raw, f"forbidden token in workflow: {forbidden}"