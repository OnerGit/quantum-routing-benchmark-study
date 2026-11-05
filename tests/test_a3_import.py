"""Import-contract tests for the frozen A3 modules inside the package layout."""

from __future__ import annotations

import sys

import routing_study.a3


def test_public_names_exposed():
    pkg = routing_study.a3
    assert pkg.ARCHITECTURE_ID == "OC-V2-A3-BIDIRECTIONAL-20260921"
    assert callable(pkg.solve)
    assert callable(pkg.prepare)
    assert pkg.FROZEN_PARAMETERS["randomness"] == "none"
    assert pkg.FROZEN_PARAMETERS["lookahead_window"] == 8


def test_frozen_modules_importable_in_package_layout():
    assert "routing_study.a3.solution" in sys.modules
    assert "routing_study.a3.placement" in sys.modules
    assert "routing_study.a3.routing" in sys.modules


def test_top_level_aliases_registered_for_frozen_imports():
    # solution.py's `import placement` / `import routing` must resolve to the package modules.
    assert sys.modules.get("placement").__name__ == "routing_study.a3.placement"
    assert sys.modules.get("routing").__name__ == "routing_study.a3.routing"


def test_frozen_module_identity_is_package_version():
    from routing_study.a3 import solution, placement, routing

    assert solution.__name__ == "routing_study.a3.solution"
    assert placement.__name__ == "routing_study.a3.placement"
    assert routing.__name__ == "routing_study.a3.routing"
    assert placement.SCAN_CAP == 16
    assert routing.LOOKAHEAD_WINDOW == 8


def test_frozen_parameters_reference_sibling_values():
    from routing_study.a3 import solution

    # These are evaluated at import time from the actual sibling modules.
    assert solution.FROZEN_PARAMETERS["placement_scan_cap"] == 16
    assert solution.FROZEN_PARAMETERS["lookahead_window"] == 8


def test_package_version_importable():
    import routing_study

    assert isinstance(routing_study.__version__, str)
    assert routing_study.__version__ == "0.1.0"