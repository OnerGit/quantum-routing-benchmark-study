"""Frozen A3 deterministic placement & routing (packaged without modification).

This package holds the byte-for-byte frozen A3 production modules
(`solution.py`, `placement.py`, `routing.py`, architecture
`OC-V2-A3-BIDIRECTIONAL-20260921`). The frozen files must not be edited; the import
compatibility bridge in ``_compat`` satisfies their original top-level import statements
inside the package layout.

Public API (stable surface used by the repository tests):

- ``solve(program, hardware_graph)`` -> ``(initial_placement, routed_program)``
- ``prepare(program, hardware_graph)`` -> ``(frozen_program, Context)``
- ``ARCHITECTURE_ID``, ``FROZEN_PARAMETERS``

Results produced by this module are NOT a re-run of the historical Q-SITE evaluation;
historical recorded scores remain ``RECORDED_HISTORICAL`` (see ``results/`` and
``docs/LIMITATIONS.md``).
"""

from __future__ import annotations

from . import _compat as _compat

_compat.install()

from . import placement as placement  # noqa: E402  (registered under top-level name for frozen imports)
from . import routing as routing  # noqa: E402
from . import solution as solution  # noqa: E402

ARCHITECTURE_ID = solution.ARCHITECTURE_ID
FROZEN_PARAMETERS = solution.FROZEN_PARAMETERS
solve = solution.solve
prepare = solution.prepare

__all__ = [
    "ARCHITECTURE_ID",
    "FROZEN_PARAMETERS",
    "solve",
    "prepare",
    "solution",
    "placement",
    "routing",
]