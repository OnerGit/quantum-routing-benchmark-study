# THIRD_PARTY.md

Third-party material referenced by this repository. **Policy: link-by-commit; third-party solver
code is never bundled, downloaded, or transcribed.**

> Note on licences: this repository's **original content** is licensed under the MIT License,
> Copyright (c) 2026 Bob Oner (see [LICENSE](LICENSE)). That license covers only the original
> material the author is entitled to license; it does **not** license the third-party repositories
> referenced below, and the presence of a license file in any of those repositories does not imply it
> is open source (a GitHub repository without a license remains default-copyright).

## 1. Q-SITE Quantum Coalition — official starter kit

- Repository: https://github.com/benmcdonough20/QSITE-2026-QuantumCoalition
- Pinned commit: `57f9a537d24c69328dedf915ad58d1d2bf505135`
- License: **MIT License — Copyright (c) 2026 Mihir Talati**
- Scope: the covered software in the official repository (starter kit modules, benchmark definitions,
  scorer, notebooks, docs). The MIT requirement — that the above copyright and permission notice be
  included in all copies or substantial portions — is satisfied by this `THIRD_PARTY.md` + `NOTICE.md`
  for any reference material; official modules are not redistributed in this repository.
- Verified module hashes (official tree): scorer `63417f23…`, benchmarks `a846053f…`, hardware
  `e00ea3a5…`, baseline_routing `ba7dfebb…`, `__init__` `e187581b…`, visualize `8feaad1d…`.

## 2. HorizonRoute (third-party solver)

- Repository: https://github.com/gavenren/qsite-2026-horizonroute-phaseguard
- Pinned commit: `399de22ba6e890ae1b99707c245d3c87f103ebf0`
- Solver module (link-only): `computing/solver.py`, SHA-256 `88d1babc…`
- License: **none for the author's own code.** The repository contains only `computing/vendor/LICENSE`
  which is the official MIT text scoped to the vendored official starter files. Author code
  (solver.py, bench, reports, demo assets) is copyright-default to the author and is **not**
  redistributed or transcribed here.
- Local reproduction evidence was produced by this project's runs (see `results/`); none of that
  evidence is the author's code.

## 3. Exact-Beam (third-party solver)

- Repository: https://github.com/Hemishahuja/QSITE-2026-QuantumCoalition-Submission
- Pinned commit: `d8c877a3cff79337876839f61d355764edd6c8d2`
- Solver module (link-only): `Computational Track/solution/solve.py`, SHA-256 `2d775edc…`
- License: the repository root has a `LICENSE` that is **byte-identical to the upstream official MIT
  (Mihir Talati)**. Because that notice was not authored for the submitter's additions, the scope is
  ambiguous; conservatively the submitter's **new code is treated as unlicensed** and is not
  redistributed or transcribed here.
- The F0 fusion adapter (`m/fusion_solver.py`) from the historical study transcribed the frozen
  Exact-Beam orchestration verbatim and is therefore **excluded** from this repository (BLOCK); a
  clean-room re-derivation, if ever needed, is out of scope for V0.1.

## 4. Conceptual references (cited, not vendored)

- SABRE — Li, Gushu; Ding, Yufei; Xie, Yuan. *Tackling the qubit mapping problem for NISQ-era quantum
  devices.* ASPLOS 2019. Referenced conceptually by third-party submissions; no code included here.
- Dependencies of this repository (networkx, and optionally matplotlib) are installed via the package
  manager and carry their own licenses; none are vendored.

## 5. Local research records and results

- `results/*.csv` and `docs/*` transcribe this study's audited research records (see
  `docs/EVIDENCE_INDEX.md`). These are original research evidence produced by this project; they are
  not third-party code.
- `internal/` and `review-packages/` contain internal audit material and are excluded from any public
  release.