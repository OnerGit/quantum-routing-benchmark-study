#!/usr/bin/env python3
"""Fetch the pinned official Q-SITE starter kit into the git-ignored `vendor/official/` dir.

Policy: official starter is MIT (link-by-commit); this repository does NOT bundle it. This script
materializes the pinned checkout locally so that optional (`pytest -m external`) reproducibility
checks can run with a frozen official scorer. It never touches any third-party solver.

Safety contract (P1-R1 + P1-R2):

1. **Fixed, confined destination.** There is no ``--dest`` option. The destination is always
   ``<repo>/vendor/official``. ``<repo>/vendor`` and every component of the destination are validated
   **before** any resolution/swap:
   - the ``vendor`` root must not itself be a symbolic link;
   - no component of the destination path may be a symbolic link (checked on the *original*
     components, not on a pre-resolved path);
   - the destination must stay lexically inside ``<repo>/vendor`` (path traversal components such as
     ``..`` are rejected).
2. **No arbitrary deletion.** The source never invokes a recursive force-delete on an arbitrary
   path. The only directories it removes are (a) the script's own ``staging`` directory (created with
   ``tempfile.mkdtemp(dir=vendor)``) and (b) a backup directory that the script itself created in
   **this run** — never a pre-existing directory.
3. **Unique backup names.** The backup directory is reserved via ``tempfile.mkdtemp`` (a guaranteed
   unique, empty, private name under ``vendor``), its empty shell is removed with ``os.rmdir``, and
   the existing checkout is then renamed onto it. If a directory with that name already existed
   before this run, it would never be chosen; pre-existing ``.official-*`` directories are never
   touched or deleted.
4. **Backup retained until final verification; rollback on any failure.** The old checkout stays in
   the backup directory until the *post-swap* hash verification of the new tree succeeds. If staged
   verification, the swap, or the post-swap verification fails, the original directory is restored
   from the backup (or removed completely if no pre-existing directory existed). If a rollback rename
   itself fails, the backup directory is left in place and its path is reported explicitly — data is
   never silently lost.
5. **Terminology.** This is a *coordinated, failure-rollback swap* (stage → verify → backup old →
   move new → post-verify → discard backup), implemented with several directory renames. It is **not**
   a single-call atomic filesystem operation: there is a brief window in which ``vendor/official``
   does not exist, and the move is only "atomic" per-rename. We do not claim otherwise.

Usage:
    uv run python scripts/fetch_official_starter.py            # fetch or refresh if needed
    uv run python scripts/fetch_official_starter.py --force    # refresh an existing valid checkout
    uv run python scripts/fetch_official_starter.py --check    # verify existing checkout only
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

OFFICIAL_URL = "https://github.com/benmcdonough20/QSITE-2026-QuantumCoalition"
OFFICIAL_COMMIT = "57f9a537d24c69328dedf915ad58d1d2bf505135"

# Pinned SHA-256 of the official starter modules (verified against the frozen official tree).
PINNED = {
    "starter_kit/scorer.py": "63417f2390d74fedc632e1fbfc747c75fe15d661fe66a71dea0931a0a49ae4b9",
    "starter_kit/benchmarks.py": "a846053ff7997b66eafbcdfad59c2376cdaf7344e441cf9e1289d257184980d7",
    "starter_kit/hardware.py": "e00ea3a5f5fd1951b3fea4636ff3c668a5834f555a103fffaf511705ce14c546",
    "starter_kit/baseline_routing.py": "ba7dfebb0681bf56345157bd513f10138c0128443622dfedfe72e5fe5808db41",
    "starter_kit/__init__.py": "e187581b997dd6285e7b1fd72c299d8948fea9ed40f604ce723f59eddfa57dfe",
    "starter_kit/visualize.py": "8feaad1dccf31dfd7dcc0e0a4e72b6983d73722cadea1816d616411333ea7713",
}

STARTER_RELPATH = "Computational Track/starter_kit"


# ---------------------------------------------------------------------- paths

def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def vendor_root() -> pathlib.Path:
    """The controlled vendor directory. Deliberately NOT resolved here: symlink checks are explicit."""
    return repo_root() / "vendor"


def default_destination() -> pathlib.Path:
    return vendor_root() / "official"


def validate_target(target: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    """Validate that ``target`` is a strict, symlink-free descendant of ``root``.

    The check runs on the **original path components** (never on a pre-resolved path) so that a
    symbolic link anywhere from ``root`` down to the leaf is detected instead of being silently
    canonicalized away. Path-traversal components (``..``) and the root itself being a symlink are
    also rejected.
    """
    root = pathlib.Path(root)
    target = pathlib.Path(target)
    if not target.is_absolute() or not root.is_absolute():
        raise ValueError("both target and root must be absolute paths")
    if ".." in target.parts or "." in target.parts:
        raise ValueError(f"path-traversal component in target: {target}")
    try:
        rel = target.relative_to(root)
    except ValueError:
        raise ValueError(f"target escapes controlled root: {target}")
    if rel.parts == ():
        raise ValueError(f"target must be strictly below root, not the root itself: {target}")
    if root.is_symlink():
        raise ValueError(f"controlled root is a symbolic link: {root}")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symbolic-link component in destination: {current}")
    if current.exists() and not current.is_dir():
        raise ValueError(f"destination exists and is not a directory: {current}")
    return current


def secure_destination() -> pathlib.Path:
    """Create (if needed) and validate the only permitted destination.

    The destination is fixed to ``<repo>/vendor/official``; no user-supplied path is accepted.
    """
    repo = repo_root()
    if ".." in repo.parts or "." in repo.parts:
        raise ValueError("repository root contains traversal components")
    vend = vendor_root()
    if not vend.is_absolute():
        raise ValueError("vendor root must be absolute")
    try:
        vend.relative_to(repo)
    except ValueError:
        raise ValueError("vendor root escapes the repository root")
    vend.mkdir(parents=True, exist_ok=True)
    if vend.is_symlink():
        raise ValueError("vendor root is a symbolic link; refusing to operate")
    return validate_target(default_destination(), vend)


# ---------------------------------------------------------------------- helpers

def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_official_tree(base: pathlib.Path) -> tuple[bool, list[str]]:
    """Return (ok, failures) for the official-tree hash pins at ``base``."""
    failures: list[str] = []
    if not base.is_dir():
        return False, [f"expected directory missing: {base}"]
    if not (base / "LICENSE").is_file():
        failures.append("LICENSE missing")
    kit = base / STARTER_RELPATH
    if not kit.is_dir():
        return False, failures + [f"starter_kit missing at {kit}"]
    for rel, want in PINNED.items():
        p = kit / pathlib.Path(rel).name
        if not p.is_file():
            failures.append(f"{rel}: MISSING")
            continue
        got = sha256(p)
        if got != want:
            failures.append(f"{rel}: hash mismatch {got}")
    return not failures, failures


def default_cloner(target: pathlib.Path) -> None:
    """Clone the official repo at the pinned commit into ``target`` (an empty temp dir)."""
    run = subprocess.run(["git", "clone", OFFICIAL_URL, str(target)],
                         capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(f"git clone failed: {run.stderr.strip() or run.stdout.strip()}")
    co = subprocess.run(["git", "-C", str(target), "checkout", "--detach", OFFICIAL_COMMIT],
                        capture_output=True, text=True)
    if co.returncode != 0:
        raise RuntimeError(f"git checkout failed: {co.stderr.strip() or co.stdout.strip()}")


def reserve_backup_name(root: pathlib.Path) -> pathlib.Path:
    """Reserve a unique backup name **inside** ``root`` without touching any existing directory.

    ``tempfile.mkdtemp`` guarantees the returned directory did not exist before this call. Its empty
    shell is immediately removed with ``os.rmdir`` (which fails rather than delete anything if the
    directory is not empty). The caller then renames the existing checkout onto this name. No
    pre-existing directory is ever inspected or deleted.
    """
    name = pathlib.Path(tempfile.mkdtemp(prefix=".official-backup-", dir=root))
    os.rmdir(name)  # empty, created by us this run
    return name


# ---------------------------------------------------------------------- main logic

def fetch_official(*, force: bool = False,
                   cloner=None,
                   verifier=verify_official_tree,
                   reporter=print) -> int:
    """Fetch/refresh the pinned official starter with a strict safety contract.

    Only ``<repo>/vendor/official`` is used. ``cloner``/``verifier`` are injectable for offline tests.
    Return codes: 0 = ok; 1 = check-only pin failure; 2 = fetch/refresh failure (data preserved,
    rollback best-effort); 3 = post-swap verification failed (rollback performed or backup reported).
    """
    dest = secure_destination()
    root = dest.parent

    existing_valid, existing_failures = (False, [])
    if dest.exists():
        existing_valid, existing_failures = verifier(dest)

    if existing_valid and not force:
        reporter("Using existing validated checkout at " + str(dest))
        for rel in PINNED:
            reporter(f"[OK] {rel}")
        return 0

    if dest.exists() and not existing_valid and not force:
        reporter("Existing destination present but validation failed:")
        for f in existing_failures:
            reporter("  - " + f)
        reporter("Refusing to overwrite without --force. Re-run with --force to replace.")
        return 4

    reporter(f"Fetching {OFFICIAL_URL} @ {OFFICIAL_COMMIT} into {dest}")

    # stage a fresh tree in a private, unique temp dir inside the controlled vendor area
    staging = pathlib.Path(tempfile.mkdtemp(prefix=".official-fetch-", dir=root))
    backup: pathlib.Path | None = None
    dest_existed = dest.exists()
    swapped = False

    try:
        if cloner is None:
            cloner = default_cloner
        cloner(staging)
        ok, failures = verifier(staging)
        if not ok:
            raise RuntimeError("staged verification failed: " + "; ".join(failures))

        if dest_existed:
            backup = reserve_backup_name(root)
            dest.rename(backup)           # old data is preserved in `backup`

        staging.rename(dest)
        swapped = True

        # ----- post-swap verification: keep the backup until this passes
        ok, failures = verifier(dest)
        if not ok:
            raise RuntimeError("post-swap verification failed: " + "; ".join(failures))

        if backup is not None:
            try:
                shutil.rmtree(backup)  # bounded: created by us this run
            except Exception as exc:  # noqa: BLE001
                reporter(f"[WARN] backup cleanup failed; retained at {backup}: {exc}")
        reporter("All six starter modules verified against pinned SHA-256. Optional external tests can now run.")
        return 0

    except Exception as exc:  # noqa: BLE001 -- keep CLI + test semantics uniform
        rollback_error: str | None = None
        try:
            if swapped and dest.exists():
                # the new tree (ours) failed verification -> set it aside and remove it
                failed = pathlib.Path(tempfile.mkdtemp(prefix=".official-failed-", dir=root))
                os.rmdir(failed)
                dest.rename(failed)
                shutil.rmtree(failed)
            if backup is not None and backup.exists():
                if not dest.exists():
                    backup.rename(dest)   # restore the pre-existing checkout
                else:
                    rollback_error = f"destination occupied during rollback; original data preserved at {backup}"
            elif swapped and not dest_existed:
                # fresh fetch failed; nothing pre-existed and the new tree was already removed
                pass
        except Exception as rb_exc:  # noqa: BLE001
            rollback_error = f"{rb_exc}"

        if rollback_error:
            reporter(f"[ERROR] rollback incomplete; original data preserved at {backup}: {rollback_error}")
        shutil.rmtree(staging, ignore_errors=True)  # staging name is free unless renamed; ours either way
        reporter(f"[ERROR] fetch/refresh failed; existing checkout preserved: {exc}")
        return 3 if "post-swap verification failed" in str(exc) else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="refresh an existing valid checkout")
    ap.add_argument("--check", action="store_true", help="verify existing checkout only")
    args = ap.parse_args()

    if args.check:
        dest = secure_destination()
        if not dest.exists():
            print("[ERROR] no checkout present (run without --check to fetch).")
            return 5
        ok, failures = verify_official_tree(dest)
        for rel in PINNED:
            print(f"[{'OK' if ok else 'FAIL'}] {rel}")
        if not ok:
            print("PIN VERIFICATION FAILED:", failures)
            return 1
        print("All six starter modules verified against pinned SHA-256.")
        return 0

    return fetch_official(force=args.force)


if __name__ == "__main__":
    sys.exit(main())