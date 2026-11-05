# NOTICE

## Quantum Routing Benchmark Study

This repository is an independent, empirical study of routing algorithms and benchmark
reproducibility originating from Q-SITE 2026 Open Computing research. It is **not endorsed by
Q-SITE**, its organizers, or any third-party team.

**Software author:** Bob Oner · **GitHub account owner:** OnerGit.

## Publication-status boundaries

Several distinct statuses are deliberately kept apart and this document declares none of them:

- **source repository availability** (no source-repository address is declared here);
- **formal tagged software release** (none is declared);
- **PyPI distribution** (none is declared);
- **academic publication or DOI** (none is declared).

A public source repository — if and when one exists — would not by itself imply a formal release, a
PyPI package, an academic publication, or a DOI. This NOTICE asserts none of these artifacts and
should not be read as implying any of them.

## License of this repository's original content

The independently authored original material in this repository (code, documentation, and research
records written for this project) is licensed under the **MIT License**, Copyright (c) 2026 **Bob
Oner** — see [LICENSE](LICENSE).

Scope: the MIT license applies only to material the author is entitled to license. It does **not**
grant rights over third-party code merely referenced by this repository, and it does not apply to the
third-party software listed below.

## Third-party software

Third-party software is **referenced by pinned commits, not bundled**. See `THIRD_PARTY.md` for the
complete list, notices, and scope statements.

- **Q-SITE Quantum Coalition starter kit** — MIT License, Copyright (c) 2026 Mihir Talati. Only the
  linked official repository is affected by that license; this repository does not redistribute its
  modules in V0.1.
- **HorizonRoute** (`gavenren/qsite-2026-horizonroute-phaseguard`) — no author license for its own
  code; linked only.
- **Exact-Beam** (`Hemishahuja/QSITE-2026-QuantumCoalition-Submission`) — repository LICENSE is the
  upstream official MIT text; the submitter's new code is unlicensed; linked only.

## Research provenance

- Historical recorded scores are labeled `RECORDED_HISTORICAL` / `LOCALLY_REPRODUCED_HISTORICAL` /
  `EXPERIMENTAL_LOCAL` in `results/`; see `docs/LIMITATIONS.md` for the meaning of each tier.
- Results apply to the six official instances (+ four synthetic held-out instances for the F0 study)
  only. No generality, optimality, production-readiness, or quantum-advantage claim is made.

## Contact / contribution

Authorship and citation metadata are prepared in [CITATION.cff](CITATION.cff) (CFF 1.2.0; author
**Bob Oner**), distinguishing **preparation** from **actual release**: no release date, DOI, paper,
or repository URL is asserted. An earlier internal draft is preserved as historical evidence under
`internal/CITATION.cff.draft`. No DOI or formal publication exists yet; nothing here claims one.