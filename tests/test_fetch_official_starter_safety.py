"""Offline safety tests for scripts/fetch_official_starter.py (P1-R2).

Everything runs against an isolated, simulated vendor root (a pytest ``tmp_path``) with injected
cloners/verifiers — never against the real ``vendor/`` directory, and never with the network.

Covered scenarios (Gatekeeper checklist):
  1. vendor root is a symlink             2. symlink inside vendor (leaf)
  3. symlink in an intermediate component 4. path traversal
  5. backup-name collision                6. collision directory contains user data
  7. clone failure                        8. staged-verification failure
  9. post-swap verification failure      10. rollback restores original data
 11. backup-cleanup failure keeps data   12. no unrelated directory is ever removed
The pinned commit and official SHA-256 constants must remain unchanged.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "fetch_official_starter.py"

_MOD = None


def load_module():
    global _MOD
    if _MOD is None:
        spec = importlib.util.spec_from_file_location("fetch_official_starter", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["fetch_official_starter"] = mod
        spec.loader.exec_module(mod)
        _MOD = mod
    return _MOD


@pytest.fixture()
def env(tmp_path, monkeypatch):
    mod = load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    vend = repo / "vendor"
    vend.mkdir()
    monkeypatch.setattr(mod, "repo_root", lambda: repo)
    monkeypatch.setattr(mod, "vendor_root", lambda: vend)
    return mod, repo, vend


def verifier_for(marker: str):
    """Accept trees that contain a file named ``marker`` at their root."""
    def _v(base: pathlib.Path):
        if (base / marker).is_file():
            return True, []
        return False, [f"missing {marker}"]
    return _v


def cloner_marker(marker: str):
    def _c(target: pathlib.Path):
        (target / marker).write_text("ok")
    return _c


def cloner_raise():
    def _c(target: pathlib.Path):
        raise RuntimeError("simulated network failure")
    return _c


def assert_no_temp_leftovers(vend: pathlib.Path):
    leftovers = [p.name for p in vend.iterdir() if p.name.startswith(".official-")]
    assert leftovers == [], f"unexpected leftover dirs: {leftovers}"


# ------------------------------------------------------------------ F1 symlink confinement

def test_rejects_vendor_root_symlink(env):
    mod, repo, vend = env
    vend.rmdir()
    target = repo.parent / "elsewhere"
    target.mkdir()
    vend.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        mod.secure_destination()


def test_rejects_dest_symlink_inside_vendor(env):
    mod, repo, vend = env
    inner = vend / "other"
    inner.mkdir()
    dest = mod.default_destination()
    dest.symlink_to(inner, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic-link component"):
        mod.secure_destination()


def test_rejects_intermediate_component_symlink(env):
    mod, repo, vend = env
    sub = vend / "sub"
    target = repo.parent / "outside-real"
    target.mkdir()
    sub.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic-link component"):
        mod.validate_target(sub / "official", vend)


def test_rejects_path_traversal(env):
    mod, repo, vend = env
    with pytest.raises(ValueError, match="path-traversal"):
        mod.validate_target(vend / "official" / "..", vend)
    with pytest.raises(ValueError, match="path-traversal"):
        mod.validate_target(vend / ".." / "x", vend)
    with pytest.raises(ValueError, match="escapes"):
        mod.validate_target(repo.parent / "out" / "official", vend)


def test_accepts_fixed_destination(env):
    mod, repo, vend = env
    dest = mod.secure_destination()
    assert dest == (vend / "official")


def test_no_user_dest_option():
    text = SCRIPT.read_text()
    assert '"--dest"' not in text and "'--dest'" not in text, "custom --dest must not exist"
    assert "--dest" not in text.replace("# never", "").split("\n")[0]


# ------------------------------------------------------------------ F2 backup collision safety

def test_backup_names_are_unique_and_never_reuse_preexisting(env):
    mod, repo, vend = env
    # pre-existing backup-like dirs WITH user data must not be picked
    pre = vend / ".official-backup-user"
    pre.mkdir()
    (pre / "keepme.txt").write_text("user data")
    seen = set()
    for _ in range(10):
        name = mod.reserve_backup_name(vend)
        assert name.parent == vend
        assert not name.exists(), "reserved name must be free after reservation"
        assert name.name not in seen
        seen.add(name.name)
    assert pre.is_dir() and (pre / "keepme.txt").read_text() == "user data"


def test_collision_dir_with_user_data_survives_swap(env):
    mod, repo, vend = env
    user = vend / ".official-backup-anything"
    user.mkdir()
    (user / "precious.txt").write_text("precious")

    dest = mod.default_destination()
    dest.mkdir()
    (dest / "ORIGINAL").write_text("old")

    rc = mod.fetch_official(force=True, cloner=cloner_marker("GOOD"),
                            verifier=verifier_for("GOOD"))
    assert rc == 0
    assert (dest / "GOOD").is_file()
    assert not (dest / "ORIGINAL").exists()
    assert user.is_dir() and (user / "precious.txt").read_text() == "precious", \
        "a pre-existing .official-backup-* dir with user data must never be touched"
    # the only `.official-*` entry allowed to remain is the pre-existing user dir, untouched
    leftovers = [p.name for p in vend.iterdir() if p.name.startswith(".official-")]
    assert leftovers == [".official-backup-anything"], f"unexpected leftover dirs: {leftovers}"


# ------------------------------------------------------------------ failure scenarios preserve data

def test_clone_failure_preserves_existing(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "GOOD").write_text("precious")

    rc = mod.fetch_official(force=True, cloner=cloner_raise(), verifier=verifier_for("GOOD"))
    assert rc == 2
    assert (dest / "GOOD").is_file()
    assert_no_temp_leftovers(vend)


def test_clone_failure_when_absent_leaves_nothing(env):
    mod, repo, vend = env
    rc = mod.fetch_official(force=True, cloner=cloner_raise(), verifier=verifier_for("GOOD"))
    assert rc == 2
    assert not mod.default_destination().exists()
    assert_no_temp_leftovers(vend)


def test_staged_verify_failure_preserves_existing(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "GOOD").write_text("precious")

    def staged_bad_cloner(target):
        (target / "NOTVERIFIED").write_text("x")   # staged tree lacks GOOD -> staged verify fails

    rc = mod.fetch_official(force=True, cloner=staged_bad_cloner, verifier=verifier_for("GOOD"))
    assert rc == 2
    assert (dest / "GOOD").is_file(), "existing checkout must survive staged-verify failure"
    assert_no_temp_leftovers(vend)


def test_post_swap_verify_failure_rolls_back(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "ORIGINAL").write_text("old-data")
    calls = {"n": 0}

    def stateful_verifier(base):
        # existing check (dest, True) -> staged (True) -> post-swap (False)
        calls["n"] += 1
        if calls["n"] <= 2:
            return True, []
        return False, ["post-swap failure (injected)"]

    rc = mod.fetch_official(force=True, cloner=cloner_marker("NEWTREE"),
                            verifier=stateful_verifier)
    assert rc == 3, "post-swap verification failure must be reported distinctly"
    assert (dest / "ORIGINAL").is_file(), "original directory must be restored after rollback"
    assert not (dest / "NEWTREE").exists(), "failed new tree must be removed on rollback"
    assert_no_temp_leftovers(vend)


def test_post_swap_verify_failure_fresh_removes_new_tree(env):
    """When no directory pre-existed, a post-swap failure must leave vendor clean."""
    mod, repo, vend = env
    calls = {"n": 0}

    def stateful_verifier(base):
        calls["n"] += 1
        if calls["n"] == 1:          # staged check (fresh: no existing pre-check) -> pass
            return True, []
        return False, ["post-swap failure (injected)"]

    rc = mod.fetch_official(force=True, cloner=cloner_marker("NEWTREE"),
                            verifier=stateful_verifier)
    assert rc == 3
    assert not mod.default_destination().exists()
    assert_no_temp_leftovers(vend)


def test_backup_cleanup_failure_keeps_data(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "GOOD").write_text("old-data")

    real_rmtree = __import__("shutil").rmtree

    def selective_rmtree(path, *a, **kw):
        if pathlib.Path(path).name.startswith(".official-backup-"):
            raise OSError("simulated cleanup failure")
        return real_rmtree(path, *a, **kw)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("shutil.rmtree", selective_rmtree)
    try:
        rc = mod.fetch_official(force=True, cloner=cloner_marker("GOOD"),
                                verifier=verifier_for("GOOD"))
    finally:
        monkeypatch.undo()
    assert rc == 0, "swap succeeded; cleanup failure is a warn-only condition"
    assert (dest / "GOOD").is_file()
    backups = [p for p in vend.iterdir() if p.name.startswith(".official-backup-")]
    assert len(backups) == 1, "backup dir must be retained when cleanup fails (data preserved)"
    assert (backups[0] / "GOOD").read_text() == "old-data"


def test_no_unrelated_dir_removed_across_failures(env):
    mod, repo, vend = env
    unrelated = vend / ".unrelated-user-data"
    unrelated.mkdir()
    (unrelated / "precious.txt").write_text("keep")
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "GOOD").write_text("old")

    # a failure path (clone failure) and a success path with collateral
    rc = mod.fetch_official(force=True, cloner=cloner_raise(), verifier=verifier_for("GOOD"))
    assert rc == 2
    assert unrelated.is_dir() and (unrelated / "precious.txt").read_text() == "keep"

    rc = mod.fetch_official(force=True, cloner=cloner_marker("GOOD"), verifier=verifier_for("GOOD"))
    assert rc == 0
    assert unrelated.is_dir() and (unrelated / "precious.txt").read_text() == "keep"
    assert_no_temp_leftovers(vend)


# ------------------------------------------------------------------ static hazards

def test_script_has_no_arbitrary_rm():
    text = SCRIPT.read_text()
    assert "rm -rf" not in text
    assert '"-rf"' not in text
    # every rmtree in the module must reference only our own bounded bookkeeping names
    import re
    allowed_args = {"backup", "staging", "failed"}
    for m in re.finditer(r"shutil\.rmtree\(([^,\)]+)", text):
        arg = m.group(1).strip()
        # strip possible `,` params already handled; tolerate leading variable names
        assert arg.split(" ")[0] in allowed_args or arg in allowed_args, f"unbounded rmtree: {arg}"


def test_pinned_hashes_and_commit_unchanged():
    text = SCRIPT.read_text()
    assert "57f9a537d24c69328dedf915ad58d1d2bf505135" in text
    assert "63417f2390d74fedc632e1fbfc747c75fe15d661fe66a71dea0931a0a49ae4b9" in text
    assert "a846053ff7997b66eafbcdfad59c2376cdaf7344e441cf9e1289d257184980d7" in text
    assert "e00ea3a5f5fd1951b3fea4636ff3c668a5834f555a103fffaf511705ce14c546" in text


def test_existing_valid_without_force_never_fetches(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "GOOD").write_text("ok")
    called = {"n": 0}

    def failing_cloner(target):
        called["n"] += 1
        raise RuntimeError("must not be called")

    rc = mod.fetch_official(force=False, cloner=failing_cloner, verifier=verifier_for("GOOD"))
    assert rc == 0
    assert called["n"] == 0
    assert_no_temp_leftovers(vend)


def test_invalid_existing_without_force_is_refused(env):
    mod, repo, vend = env
    dest = mod.default_destination()
    dest.mkdir()
    (dest / "SENTINEL").write_text("precious")
    called = {"n": 0}

    def failing_cloner(target):
        called["n"] += 1
        raise RuntimeError("must not be called")

    rc = mod.fetch_official(force=False, cloner=failing_cloner, verifier=verifier_for("GOOD"))
    assert rc == 4
    assert called["n"] == 0
    assert (dest / "SENTINEL").read_text() == "precious"