# Methodology

This document describes how the historical recorded scores and the local reproductions were produced,
and what evidence each result table carries. No experimental work was re-run for this repository build;
all figures below are transcribed from the audited research records listed in
[docs/EVIDENCE_INDEX.md](EVIDENCE_INDEX.md).

## 1. Scoring contract

- Scorer: the **official Q-SITE computational-track scorer** (frozen commit
  `57f9a53…`, module SHA `63417f23…`).
- Cost model used by the official scorer: `score = swaps + 0.5 * depth`.
- The internal Objective function used by A3 for its own candidate selection is
  `2 * swaps + depth`; the **reported** scores always use the official scorer.

## 2. Instances

The six official computational-track benchmark instances:

`ghz_star`, `chain_trotter`, `ladder_trotter`, `qaoa_random`, `dense_random`, `vqe_layers`.

Instance definitions (hardware + programs) follow the official starter kit and are **not bundled**;
they are referenced by commit SHA in [THIRD_PARTY.md](../THIRD_PARTY.md).

The F0 fusion study additionally used four pre-registered synthetic held-out instances (`H1`–`H4`)
whose generators are documented in the F0 review package.

## 3. Methods vs. budgets — NOT homogeneous

| Method | Budget semantics | Measured runtime (our host) |
|---|---|---|
| A3 (frozen pipeline) | fixed, no runtime budget | milliseconds per case |
| HorizonRoute | quality-bounded (beam width/parameters) | ~65 s total portfolio |
| Exact-Beam | anytime, `time_budget=20 s` per instance | hard cases ~20.2–20.4 s wall |

Consequence: the six-case totals are scores under **different clock-budget regimes**. They are
evidence of *per-solver behavior at author defaults on these instances*, **not** an apples-to-apples
"who wins a fixed time budget" ranking. The F0 study is the only comparison with a **common** 20 s
per-instance budget.

## 4. Evidence tiers (used in every table)

| Tier | Meaning |
|---|---|
| `RECORDED_HISTORICAL` | produced by the historical frozen run; source-hash verified here; **not re-run** |
| `LOCALLY_REPRODUCED_HISTORICAL` | produced by this project on this host with the frozen official scorer (single-shot) |
| `EXPERIMENTAL_LOCAL` | produced in the F0 one-shot study on this host |
| `AUTHOR_REPORTED` | as claimed in the external repository/report; not executed here |

## 5. Reproduction runs (this project)

- **HorizonRoute (E2-B).** Author-native `benchmark.py --width 900 --heldout 4` and a controlled-harness
  run, both at author defaults, frozen scorer, single-shot, Python 3.14.7 / networkx 3.7. Total 68.5.
- **Exact-Beam (E4-B).** Author-native `verify_official.py --budget 20` and a controlled-harness run;
  the controlled outputs were additionally **independently re-scored** by a fresh import of the frozen
  official scorer (0 mismatches). Total 67.5.
- **F0 (one-shot fusion).** Arms B0/F1/F2 × seeds {0,1,2} × 6 official instances, per-instance 20 s
  budget incl. A3 preprocessing, OS cap budget+1.5 s, then an independent official-scorer rescore of all
  78 rows (0 mismatches).
- All E2/E4 controlled runs enforced per-case and total budgets (recorded in evidence).

## 6. A3 frozen-solve interface used in this repository

- The packaged A3 is byte-for-byte the frozen production code (`OC-V2-A3-BIDIRECTIONAL-20260921`).
- `solve(program: list[tuple], hardware_graph: networkx.Graph)` → `(initial_placement, routed_program)`.
- Deterministic; no RNG; valid for simple undirected connected integer-labeled hardware graphs.
- Import compatibility inside this package is handled by `src/routing_study/a3/_compat.py` (the frozen
  files are never rewritten).

## 7. Known limitations of the comparisons

1. Budget heterogeneity (section 3) — do not read the totals as an equal-budget ranking.
2. Single-shot runs; no confidence intervals; Exact-Beam is load-sensitive (documented qaoa
   11.5↔12.5 variance).
3. F0 hard instances exceeded the nominal 20 s wall on some rows (measured ~20.35–20.39 s; effective
   cap = budget + 1.5 s).
4. F2 per-row implementation concern (index/critical-path caveat from the F0 audit) — the F2 result is
   reported as-is and is **not** generalized to a statement about critical-path or Pareto methods.
5. Only the six official instances (+ four F0 synthetic held-out) are covered; no generality claim.
6. Stretch-bonus 26.5 is `AUTHOR_REPORTED`/unverified and intentionally excluded.