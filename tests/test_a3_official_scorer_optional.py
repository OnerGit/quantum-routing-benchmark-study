"""OPTIONAL official-scorer regression check for the migrated frozen A3.

This test is **skipped by default**: it requires the pinned official starter checkout at
`vendor/official/` (MIT, link-by-commit), which is git-ignored and fetched by
`scripts/fetch_official_starter.py`.

Run it with:
    uv run pytest -m external

IMPORTANT framing: a passing run verifies that the **migrated frozen A3** reproduces the
recorded per-case outputs with the frozen official scorer. It is a *migration/reproducibility*
check. It does NOT re-establish the historical Q-SITE claim; the recorded scores keep the
`RECORDED_HISTORICAL` label.
"""

from __future__ import annotations

import csv
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
VENDOR = REPO / "vendor" / "official"
KIT_DIR = VENDOR / "Computational Track"

pytestmark = pytest.mark.external

requires_vendor = pytest.mark.skipif(
    not (VENDOR / "LICENSE").is_file(),
    reason="official starter checkout not present (scripts/fetch_official_starter.py)",
)


def _load_official_starter():
    sys.path.insert(0, str(KIT_DIR))
    import starter_kit.benchmarks as benchmarks  # type: ignore
    import starter_kit.hardware as hardware  # type: ignore
    import starter_kit.scorer as scorer  # type: ignore

    return benchmarks, hardware, scorer


@requires_vendor
def test_official_starter_hashes_pin():
    """Sanity: the vendored starter modules exist and import cleanly."""
    _load_official_starter()
    from starter_kit import benchmarks  # noqa: F401


@requires_vendor
def test_frozen_a3_reproduces_recorded_official_scores():
    benchmarks, hardware, scorer = _load_official_starter()
    graph = hardware.build_hardware_graph()

    from routing_study.a3 import solve

    recorded = {}
    with (REPO / "results" / "a3_historical.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["benchmark"].upper() == "TOTAL":
                continue
            recorded[row["benchmark"]] = float(row["score"])

    assert set(recorded) == set(benchmarks.BENCHMARKS)

    results = {}
    for name, program in benchmarks.BENCHMARKS.items():
        placement, routed = solve(list(program), graph)
        summary = scorer.score_summary(list(program), graph, placement, list(routed))
        assert summary["valid"], f"{name}: routed program invalid: {summary['message']}"
        results[name] = {"score": summary["score"], "swaps": summary["swap_count"],
                         "depth": summary["depth"], "recorded": recorded[name],
                         "match": summary["score"] == recorded[name]}

    mismatches = {k: v for k, v in results.items() if not v["match"]}
    total = sum(v["score"] for v in results.values())
    assert not mismatches, f"per-case mismatches vs recorded historical: {mismatches}"
    assert total == sum(recorded.values()), f"recorded total mismatch: {total} vs {sum(recorded.values())}"