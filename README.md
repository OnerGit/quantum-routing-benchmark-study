# Quantum Routing Benchmark Study

An independent empirical study of quantum circuit **placement and routing heuristics**, emphasizing
reproducible benchmark evaluation, search-budget transparency, and evidence-backed comparison —
originating from Q-SITE 2026 Open Computing research.

> **Positioning.** This is an independent research artifact. It is **not endorsed by Q-SITE**, its
> organizers, or by any third-party team. All historical results are reported strictly with their
> provenance and evidentiary limits (see [docs/LIMITATIONS.md](docs/LIMITATIONS.md)). New or modified
> scientific claims are **not** asserted here; this study reports recorded and locally reproduced
> evidence only.

**Software author:** Bob Oner · **GitHub account owner:** [OnerGit](https://github.com/OnerGit).
Original-content license: **MIT** ([LICENSE](LICENSE)). Citation metadata:
[CITATION.cff](CITATION.cff).

## 1. Problem and Study Scope

**The routing problem.** A compiled quantum circuit must be made to run on a device whose qubits are
connected by a fixed, sparse coupling graph. When a two-qubit gate acts on two logical qubits that are
not physically adjacent, the compiler must insert **SWAP** operations to move the qubits together.
Every SWAP is an extra operation; chains of SWAPs lengthen the schedule. The routing problem is
therefore a trade-off between two resources:

- **SWAP count** — additional operations injected into the circuit (instruction overhead);
- **circuit depth** — the longest dependency chain of the routed schedule (latency).

The official benchmark used in this study scores a routed circuit with the composite objective
`score = swaps + 0.5 * depth`: lower is better, and a placement/routing heuristic must decide both
where the logical qubits start and how SWAPs are interleaved.

The study covers an original deterministic routing implementation, independent reproduction of
third-party benchmark scores, and controlled experiments with combined search mechanisms. These are
**different evidence types**, not a single equal-budget competition. The formal research questions
are documented in the [Research Report](docs/RESEARCH_REPORT.md#research-questions-and-evidence-path).

## 2. Research Contributions

- **Audited original implementation.** Preserve the fully **deterministic** A3 placement-and-routing
  pipeline (`OC-V2-A3-BIDIRECTIONAL-20260921`) **byte-for-byte**, together with its recorded historical
  result and source-integrity checks (`src/routing_study/a3/`).
- **Independent benchmark reproduction.** Reproduce the reported six-instance scores of HorizonRoute
  and Exact-Beam using the frozen official scorer, while respecting third-party source licensing;
  those solvers are **linked, not bundled**.
- **Controlled fusion experiment.** Evaluate A3-derived placement feedback (F1) and critical-path/
  Pareto additions (F2) against a frozen Exact-Beam reference (B0) under a common nominal per-case
  budget, including the documented negative result and implementation caveats.
- **Traceable evidence and limitations.** Keep recorded history, local reproduction, and new
  experimental observations distinct; disclose differing budgets, seeds, and interpretation limits.

## 3. Algorithms Studied

- **A3 — Deterministic bidirectional routing** (`src/routing_study/a3/`; frozen, byte-for-byte).
  Interaction-weighted greedy + rank seeds, strict full best-improvement refinement, strict-progress
  routing (`distance_after = distance_before - 1`), lookahead window 8, forward + feedback passes,
  winner by `2*swaps + depth` over a bounded layout pool. Fully deterministic (no RNG).
- **HorizonRoute** — zero-SWAP embedding placement, bounded dual-pass beams with future-distance and
  critical-path projection, at its author defaults. **Not bundled** (link-only).
- **Exact-Beam** — anytime portfolio over ranked starts with escalating beam widths and a
  monotone accept rule; **not bundled** (link-only).

See [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md) and [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## 4. Benchmark Setup

- Scoring and instance definitions follow the **official Q-SITE starter** (MIT, link-by-commit):
  https://github.com/benmcdonough20/QSITE-2026-QuantumCoalition @ `57f9a53`.
- Instances: the six official computational-track benchmarks (`ghz_star`, `chain_trotter`,
  `ladder_trotter`, `qaoa_random`, `dense_random`, `vqe_layers`).
- The F0 study additionally used four pre-registered synthetic held-out instances.
- **Runtime budgets were NOT homogeneous** across methods — see the budget caveat below.

## 5. Results and Evidence Limits

The following are **recorded or locally reproduced observations**, classified by evidence source.
Lower scores are better under the official objective, but the methods were **not** all evaluated
under identical runtime budgets.

| Method | Total (6 official cases) | Evidence status |
|---|---:|---|
| A3 (original submission) | **110.0** | `RECORDED_HISTORICAL` (frozen source, recorded run) |
| HorizonRoute (local reproduction) | **68.5** | `LOCALLY_REPRODUCED_HISTORICAL` |
| Exact-Beam (local reproduction) | **67.5** | `LOCALLY_REPRODUCED_HISTORICAL` |
| F0 B0 / F1 (equal 20 s budget, 3 seeds) | **67.5 / 67.5** | `EXPERIMENTAL_LOCAL` (negative result) |
| F0 F2 (equal 20 s budget, 3 seeds) | **68 / 69 / 68** | `EXPERIMENTAL_LOCAL` (regression) |

**Interpretation boundary.** A3 is a frozen, recorded historical result; the third-party solver
figures are single local reproductions; F0 reports three seeded experimental runs. Budget regimes
still differ across these groups (fast-fixed A3, quality-bounded HorizonRoute, anytime ≤20 s
Exact-Beam, nominal equal 20 s per case for F0 with disclosed wall-clock overruns). The table is
**not** an equal-budget leaderboard and establishes no generality, optimality, asymptotic,
production, or quantum-advantage claim. F0 did **not** meet its pre-registered improvement target
(`≤ 65.5` in at least 2/3 seeds); the F2 regression is subject to its documented logic/index caveat.
The stretch-bonus figure (26.5) remains excluded and unverified.

Per-case detail lives in audited, immutable CSV files:

- [results/a3_historical.csv](results/a3_historical.csv) — A3 (110.0, `RECORDED_HISTORICAL`)
- [results/horizonroute_reproduction.csv](results/horizonroute_reproduction.csv) — 68.5, locally reproduced
- [results/exact_beam_reproduction.csv](results/exact_beam_reproduction.csv) — 67.5, locally reproduced
- [results/fusion_experiment.csv](results/fusion_experiment.csv) — B0/F1 67.5; F2 68/69/68

Each row carries `source`, `status`, `budget`/`seeds`, and an evidence pointer. A compact
**Result Evidence Matrix** (method · scope · result · classification · seed/budget · reproduction ·
limitations) is provided in [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md). The F0 research
decision was `NO_GO_FURTHER_RESEARCH`.

**Further reading:** the [Research Report](docs/RESEARCH_REPORT.md) contains the research questions
and full analysis; [Methodology](docs/METHODOLOGY.md) describes the algorithms;
[Evidence Index](docs/EVIDENCE_INDEX.md) traces the records; [Limitations](docs/LIMITATIONS.md)
documents the caveats; and [Reproducibility](docs/REPRODUCIBILITY.md) distinguishes environment
bootstrap from offline test execution.

## 6. Quick Start

Requirements: [uv](https://docs.astral.sh/uv/) (Python 3.14 managed automatically).

```bash
uv sync --frozen        # create the environment from the committed uv.lock (needs network on FIRST run)
uv run pytest           # run the default offline test suite
uv run python -c "from routing_study.a3 import solve, prepare; print(solve.__name__, prepare.__name__)"
```

The default test suite is fully **offline** (no official starter, no third-party solver, no
original-project paths) once the environment exists. For a **fully offline bootstrap** with a warm uv
cache use `uv sync --frozen --offline`. See [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for the
exact distinction between offline test execution, fresh bootstrap, and cached-offline bootstrap.

## 7. Reproducibility

- The frozen A3 modules are migrated byte-for-byte and hash-verified
  (`src/routing_study/a3/_frozen_hashes.json`); integrity is enforced by
  `tests/test_a3_integrity.py`.
- All results tables in [results/](results/) carry `source`, `status`, `budget`, `instances`, `seeds`,
  and evidence pointers, and are checked by `tests/test_claims_integrity.py`.
- Optional official-scorer checks require a pinned checkout of the official starter
  (`scripts/fetch_official_starter.py` → `vendor/official/`, git-ignored); those tests are skipped by
  default (see `tests/test_a3_official_scorer_optional.py`).
- Running the third-party solvers themselves is **out of scope for this repository** (unlicensed
  source, link-only) — see [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## 8. Limitations (summary)

1. A3 110.0 is recorded **historical** evidence of the frozen revision, not a modern re-run.
2. The six-instance totals are **not** evidence of general/asymptotic superiority; budgets differed
   (A3 fast & fixed; HorizonRoute ~65 s; Exact-Beam anytime ≤ 20 s/case).
3. F0 hard instances slightly exceeded the nominal 20 s per-case wall budget (measured
   `elapsed ~20.35–20.39 s`; effective cap = budget + 1.5 s).
4. The F2 (critical-path + Pareto) variant regressed, but the F0 audit also flagged a potential
   logic/index concern in that variant — **no** general conclusion about critical-path or Pareto
   methods is drawn.
5. All results are single-shot, on a small instance set; the F0 study added 4 synthetic held-out
   instances only.
6. Stretch-bonus figure **26.5** is `AUTHOR_REPORTED`/unverified and excluded.
7. No quantum-advantage, global-optimality, or general-superiority claim is made or implied.

Full text: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## 9. Third-Party Attribution

- Official starter kit — MIT, © 2026 Mihir Talati (link-by-commit).
- HorizonRoute — no repository license for its own code; **linked, not bundled**.
- Exact-Beam — repository LICENSE is the upstream official MIT; the submitter's new code is
  **unlicensed**; **linked, not bundled**.
- SABRE (Li, Ding, Xie, ASPLOS 2019) referenced conceptually by third parties; no code vendored here.

See [THIRD_PARTY.md](THIRD_PARTY.md) and [NOTICE.md](NOTICE.md).

## 10. License and Publication Status

- **License: MIT** for the independently authored original content of this repository
  ([LICENSE](LICENSE)). Copyright (c) 2026 **Bob Oner** (software author). It does **not** grant
  rights over the third-party material referenced and not bundled here — see
  [THIRD_PARTY.md](THIRD_PARTY.md).
- **Citation metadata:** see [CITATION.cff](CITATION.cff) (CFF 1.2.0; author Bob Oner). No release
  date, DOI, paper, or source-repository URL is declared in the citation metadata; each is a distinct
  status and no such artifact should be inferred from this document.
- **Source / publication status — read with care.** Several distinct statuses are deliberately kept
  apart:
  - **source repository availability** — the public GitHub source repository hosting this README is
    available to readers;
  - **formal tagged software release** — none has been created or declared;
  - **PyPI distribution** — none has been created or declared;
  - **academic publication or DOI** — none has been created or declared.

  Public source availability **does not imply** a formal release, a PyPI package, an academic
  publication, or a DOI. The citation metadata intentionally does not assert any of those artifacts.
- `internal/` and `review-packages/` are internal-only and excluded from this public repository and
  any future formal release.

## Project maintenance notes

- This repository does **not** bundle any third-party solver source and does not claim their
  endorsement.
