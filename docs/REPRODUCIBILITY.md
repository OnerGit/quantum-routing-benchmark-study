# Reproducibility

This document distinguishes three distinct operations so that "offline" is never overstated.

## A. Offline scientific test execution

Running the test suite against an **already-created** environment does **not** need the network, the
official starter, any third-party solver, or the original research workspace.

```bash
# environment already exists (created as in B or C below)
uv run pytest                     # default suite
uv run pytest -q -m external     # optional checks, only if vendor/official is present
```

What the offline suite verifies:

- frozen A3 source hash integrity (`tests/test_a3_integrity.py`);
- A3 import inside the new package layout (`tests/test_a3_import.py`);
- A3 smoke / output contract / determinism on synthetic hardware (`tests/test_a3_smoke.py`);
- results-table provenance & claims hygiene (`tests/test_claims_integrity.py`);
- repository-contract and metadata hygiene (`tests/test_repository_contract.py`,
  `tests/test_metadata_validation.py`);
- publication-safety static audit (`tests/test_publication_safety.py`);
- fetch-script safety contract, offline-negative (`tests/test_fetch_official_starter_safety.py`).

The two `-m external` tests **skip automatically** unless the pinned official-starter checkout is
present in `vendor/official/`. On a fresh machine, the default run therefore executes the full offline
suite with zero external downloads.

## B. Fresh environment bootstrap (needs network on first run)

```bash
uv sync --frozen
```

This *creates* the environment from the committed `uv.lock`:
- it installs the pinned Python interpreter (`.python-version`) if it is not already available to uv;
- it downloads the resolved packages (network + package indexes / caches);
- it **does not** re-resolve: the lock is authoritative and must match (`uv lock --check`).

`uv sync --frozen` is therefore **not** a network-free operation on first use. It becomes
network-free only when the interpreter and all wheels are already available (cached) — see C.

## C. Fully offline bootstrap with cached dependencies

A *fully offline* bootstrap is possible only when the required artifacts are already present locally:

- the pinned Python (`.python-version`) is installed for uv;
- the uv cache already contains every locked wheel/package (seed it once with network, then reuse);
- the `vendor/official/` checkout (if the `-m external` checks are wanted) already exists.

```bash
# with a warm uv cache:
uv sync --frozen --offline          # never touches the network
uv run pytest                       # offline scientific tests
```

Without a warm cache, `--offline` will fail; that is expected and correct behaviour. The repository
commits only its own `uv.lock`; it does not and cannot bundle the wheel cache.

## Lockfile & environment policy

- The repository **commits its own** `uv.lock` (generated from its `pyproject.toml`); `uv lock --check`
  and `uv sync --frozen` are part of the build gate.
- Lockfiles or prompts from the original research environment (`retrospective/**/uv.lock`,
  `.../exactbeam-native.lock`, `pyvenv.cfg`) are **not migrated** into this repository.
- `.venv/`, caches, and `vendor/official/` are git-ignored and never published.

## A3 migration verification (optional external)

- `src/routing_study/a3/` holds byte-for-byte copies of the frozen modules; SHA-256 are pinned in
  `src/routing_study/a3/_frozen_hashes.json` and asserted by `tests/test_a3_integrity.py`.
- Optional official-scorer regression (against the pinned MIT starter fetched by
  `scripts/fetch_official_starter.py`):

  ```bash
  uv run python scripts/fetch_official_starter.py   # confined to vendor/official, hash-verified
  uv run pytest -q -m external
  ```

  This verifies that the **migrated frozen A3** reproduces the recorded per-case outputs with the
  frozen official scorer. It is a migration check, **not** a re-run of the historical submission; the
  recorded scores keep their `RECORDED_HISTORICAL` labels.

## Running the third-party solvers

HorizonRoute and Exact-Beam new code is **unlicensed**; this repository therefore does **not** bundle,
download, or execute those solvers. It links to their pinned commits and preserves their reproduction
evidence. Readers must obtain those public sources themselves under whatever terms their authors
provide.

## Environment recording (P1 build)

- Python: `.python-version` = 3.14; materialized by uv (build host: Python 3.14.7).
- Tooling: uv 0.13.7 (installed into the host user environment to satisfy the lock/sync gate).
- Dependencies: networkx (runtime), pytest + PyYAML + matplotlib (dev / optional-external).
- `uv lock --check` and `uv sync --frozen` passed at build time.