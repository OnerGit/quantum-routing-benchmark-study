"""Import-compatibility bridge for the frozen A3 modules.

The frozen A3 sources (`solution.py`, `placement.py`, `routing.py`) were frozen in a layout in which
`solution.py` imported its siblings by bare top-level names (`import placement`, `import routing`).
In this repository the same files are relocated into the `routing_study.a3` package without modifying
their bytes. This bridge imports the siblings and registers them under their original top-level names
so the frozen import statements resolve to the already-loaded package modules.

This is the ONLY place where package-level aliasing is performed; the frozen module files themselves
are never rewritten (see `src/routing_study/a3/_frozen_hashes.json` and `tests/test_a3_integrity.py`).
"""

from __future__ import annotations

import importlib
import sys

_ALIASES = {"placement": "routing_study.a3.placement", "routing": "routing_study.a3.routing"}


def install() -> None:
    """Import the A3 sibling modules and register them under their original top-level names.

    The registration is unconditional from inside this package's controlled environment: the frozen
    ``solution.py`` requires the bare ``placement`` / ``routing`` names to resolve to these modules.
    """
    for name, target in _ALIASES.items():
        mod = importlib.import_module(target)
        sys.modules[name] = mod
    # The frozen module must see itself importable under its canonical names; double-check.
    sys.modules.setdefault("routing_study", sys.modules.get("routing_study"))