# Research Report

## 1. Problem definition

Compiling a quantum circuit for a device with a sparse coupling graph requires **routing**: making the
logical two-qubit interactions physically adjacent by inserting SWAP operations, while minimizing a
composite cost (official score `swaps + 0.5 * depth`). This study examines (a) how a deterministic
placement+routing pipeline (A3) behaves on the official instances, (b) whether two third-party solvers'
**reported** scores are independently reproducible on a different host with the frozen official scorer,
and (c) whether combining A3 placement feedback and critical-path/Pareto ideas with an Exact-Beam-style
solver improves results under a common wall-clock budget.

## 2. Methods overview

| Method | Placement | Routing / search | Determinism |
|---|---|---|---|
| A3 | interaction-weighted greedy + sorted-rank seeds, strict full best-improvement refinement, feedback layouts | strict-progress SWAP selection, lookahead window 8, forward+feedback passes, winner by `2·swaps+depth` | fully deterministic |
| HorizonRoute | zero-SWAP embedding pre-pass + lazy placement | shortest-path SWAP enumeration, bounded dual-pass beams (width 900→500), future-distance + critical-path projection | deterministic given env |
| Exact-Beam | lazy + prefix embeddings + annealed starts, SABRE-style bidirectional refinement | anytime portfolio, escalating beam widths 8→4096, monotone accept | seeded RNG; load-sensitive |

Details: [docs/METHODOLOGY.md](METHODOLOGY.md).

## 3. Data provenance

- Frozen sources recorded in [docs/EVIDENCE_INDEX.md](EVIDENCE_INDEX.md).
- Historical run records: `qsite-2026/…/evidence/gate7e/a3_authority.json` (A3),
  `…/evidence/e2b/*` (HorizonRoute epoch), `…/evidence/e4b/*` (Exact-Beam epoch),
  `…/open-computing-fusion/…` (F0).

## 4. Results

### 4.1 A3 — recorded history (status: `RECORDED_HISTORICAL`)

| Case | shift | swaps | depth | score |
|---|---|---|---|---|
| ghz_star | — | 4 | 7 | 7.5 |
| chain_trotter | — | 1 | 10 | 6.0 |
| ladder_trotter | — | 9 | 11 | 14.5 |
| qaoa_random | — | 11 | 17 | 19.5 |
| dense_random | — | 42 | 35 | 59.5 |
| vqe_layers | — | 0 | 6 | 3.0 |
| **TOTAL** | **110.0** | 67 | 86 | 6/6 valid · 29/29 regression |

**Important:** these are the recorded results of the frozen A3 revision, hash-verified but **not
re-run** for this claim.

### 4.2 HorizonRoute — local reproduction (status: `LOCALLY_REPRODUCED_HISTORICAL`)

| Case | swaps | depth | score | runtime |
|---|---|---|---|---|
| ghz_star | 2 | 9 | 6.5 | ~8 s |
| chain_trotter | 0 | 9 | 4.5 | <1 s |
| ladder_trotter | 3 | 7 | 6.5 | ~13 s |
| qaoa_random | 6 | 13 | 12.5 | ~7 s |
| dense_random | 24 | 23 | 35.5 | ~13 s |
| vqe_layers | 0 | 6 | 3.0 | <1 s |
| **TOTAL** | **68.5** | 35 | 67 | 6/6 valid |

### 4.3 Exact-Beam — local reproduction (status: `LOCALLY_REPRODUCED_HISTORICAL`)

| Case | swaps | depth | score | runtime |
|---|---|---|---|---|
| ghz_star | 2 | 9 | 6.5 | ~3 s |
| chain_trotter | 0 | 9 | 4.5 | <1 s |
| ladder_trotter | 3 | 7 | 6.5 | ~20 s |
| qaoa_random | 6 | 11 | 11.5 | ~20 s |
| dense_random | 24 | 23 | 35.5 | ~20 s |
| vqe_layers | 0 | 6 | 3.0 | <1 s |
| **TOTAL** | **67.5** | 35 | 65 | 6/6 valid · independent rescore 0 mismatch |

### 4.4 F0 fusion study (status: `EXPERIMENTAL_LOCAL`) — official instances

| Arm / mechanism | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| B0 (frozen Exact-Beam reference) | 67.5 | 67.5 | 67.5 |
| F1 (+ A3 placement candidates) | 67.5 | 67.5 | 67.5 |
| F2 (+ critical-path ordering + Pareto retention) | 68.0 | 69.0 | 68.0 |

Pre-registered target `total ≤ 65.5` in ≥2/3 seeds → **NOT MET**. All 54 official + 24 held-out rows
independently rescored valid (0 mismatches).

### 4.5 Result Evidence Matrix (compact)

| Method | Experimental scope | Recorded result | Evidence classification | Seeds / budget | Reproduction availability | Main limitations |
|---|---|---|---|---|---|---|
| A3 (frozen submission) | 6 official instances | 110.0 (67 swaps, depth 86) | `RECORDED_HISTORICAL` | deterministic; no RNG; no runtime budget (ms) | source in this repo (byte-for-byte); recorded results, not a re-run | historical run only; per-case runtime microsecond-scale |
| HorizonRoute | 6 official instances | 68.5 | `LOCALLY_REPRODUCED_HISTORICAL` | author defaults; quality-bounded (~65 s portfolio) | evidence + pinned commit link; solver not bundled (unlicensed) | single-shot; different budget regime |
| Exact-Beam | 6 official instances | 67.5 | `LOCALLY_REPRODUCED_HISTORICAL` | anytime, ≤20 s/case (wall ~20.2–20.4 s) | evidence + pinned commit link; solver not bundled (unlicensed) | single-shot; load-sensitive |
| F0 B0 | 6 official + (4 held-out) | 67.5 / seed {0,1,2} | `EXPERIMENTAL_LOCAL` | 20 s/case incl. A3 preproc; OS cap +1.5 s | results CSVs + F0 review ref | equal-budget but one-shot; 20 s wall deviation disclosed |
| F0 F1 | 6 official + (4 held-out) | 67.5 / seed {0,1,2} | `EXPERIMENTAL_LOCAL` | 20 s/case | as above | placement-feedback benefit `NOT_EVIDENCED` |
| F0 F2 | 6 official | 68.0 / 69.0 / 68.0 | `EXPERIMENTAL_LOCAL` | 20 s/case | as above | regression vs B0; F2 critical-path/index caveat — no general verdict |

Reading rule: cells mix different budget regimes; rows are **not** comparable as a single
equal-budget ranking. `26.5` (stretch) is excluded (unverified, rule removed upstream).

## 5. Findings / negative results

1. **Third-party score reproducibility:** both 68.5 (HorizonRoute) and 67.5 (Exact-Beam) were
   reproduced on this host with the frozen official scorer. Exact-Beam's qaoa 11.5 replicates the
   author's quieter-machine figure (the author also documents 12.5 under load) — consistent with an
   anytime, load-sensitive search.
2. **A3 placement feedback (F1):** adding A3-derived layout candidates to the Exact-Beam start pool
   produced **no improvement** under the equal 20 s budget → `PLACEMENT_FEEDBACK_BENEFIT = NOT_EVIDENCED`.
3. **Critical-path ordering + Pareto retention (F2):** the variant **regressed** vs B0 on qaoa/dense;
   the mechanism benefit is `NOT_EVIDENCED` **and** the F0 audit flagged a potential index/critical-path
   defect in this variant, so no general conclusion about those ideas is drawn.
4. **Fusion outcome:** no arm met the pre-registered target; research decision:
   `NO_GO_FURTHER_RESEARCH`.

## 6. Interpretability limits

- Budget regimes differ across the three algorithms (fast-fixed vs quality-bounded vs anytime-20 s);
  the totals in 4.1–4.3 are **not** an equal-budget ranking.
- All observations are single-shot on the six official instances (+4 synthetic held-out for F0).
- No optimality, asymptotic, generality, production-readiness, or quantum-advantage claim is made.

## 7. Honest framing for citations

Prefer wording such as: *"an independently reproduced (or recorded) total of X on the six official
instances under [method-specific budget], with the stated limitations"*. Do **not** state that any
method "wins/beats/outperforms" in general, and do not present the local reproduction of a third-party
solver as the author's own official score.