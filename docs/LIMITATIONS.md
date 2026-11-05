# Limitations & Disclosures

This document collects every caveat that must accompany the results reported in this repository. It
mirrors the P0 claims-and-limitations audit (`P0_CLAIMS_AND_LIMITATIONS.md` in the review package) so
that the public-facing tree carries the same rigor as the internal record.

## A. Result statuses — never blur the tiers

| Result | Tier used in this repo | What it means |
|---|---|---|
| A3 110.0 | `RECORDED_HISTORICAL` | frozen revision, historical run, hash-verified, **not re-run** |
| HorizonRoute 68.5 | `LOCALLY_REPRODUCED_HISTORICAL` | our host, frozen official scorer, single-shot |
| Exact-Beam 67.5 | `LOCALLY_REPRODUCED_HISTORICAL` | our host, frozen official scorer, independent rescore |
| F0 B0/F1/F2 | `EXPERIMENTAL_LOCAL` | one-shot, equal 20 s budget, independent rescore |

Smoke/regression runs inside this repository (e.g., the optional official-scorer test) verify the
moved source against recorded outputs; they **never** relabel a historical score as a fresh
experiment.

## B. Budget heterogeneity

A3: fast/fixed (ms). HorizonRoute: quality-bounded (~65 s total). Exact-Beam: anytime ≤20 s per
instance (hard cases measured ~20.2–20.4 s wall). Therefore cross-method totals are not an
equal-budget ranking and imply no generality advantage.

## C. F0 time-budget deviation

In the F0 (and E4-B) runs, hard instance walls slightly exceeded the nominal 20 s per-instance budget
(measured `solver_wall_s` up to ~20.1, `elapsed_wall_s` up to ~20.39; OS kill cap set at budget+1.5 s).
The results are valid **within the effective cap** but not strictly "≤20 s" per row. Any re-use of these
figures must reproduce this disclosure.

## D. F2 implementation caveat

The F2 arm (critical-path ordering + bounded Pareto retention) regressed, but the F0 audit flagged a
potential logic/index concern in that variant's critical-path implementation. Consequently the F2
numbers are reported as-is and support only the claim *"this fused variant regressed under this
protocol"*. No statement that critical-path or Pareto methods are generally invalid is permitted.

## E. Instance & statistics scope

- Official results: the six official computational-track instances only.
- F0 held-out comparison: four generated synthetic instances (pre-registered); not organizer tests.
- Single-shot; no confidence intervals; Exact-Beam is load-sensitive (documented 11.5↔12.5 on qaoa).

## F. Excluded data

- Stretch-bonus figure **26.5**: `AUTHOR_REPORTED`, unverified, and dependent on a rule text that was
  removed from the official README upstream → excluded from this repository.

## G. Forbidden claims

This repository must never be cited to support:

- quantum advantage / quantum speedup;
- global optimality of any routing/placement result;
- general (out-of-instance) superiority of any algorithm;
- production readiness of any solver.

## H. Third-party boundary

HorizonRoute and Exact-Beam **new solver code is unlicensed** (no author license statement). This
repository links to their pinned commits and carries their research evidence; it does **not** bundle or
claim authorship of their code, and it does **not** promise that a reader can run those solvers purely
from this repository.