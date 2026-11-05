"""Adapted benchmark-instance loaders.

The official Q-SITE starter kit (MIT, link-by-commit) defines the canonical benchmark
instances, hardware, and scorer used for the historical evaluations. Under the repository
V0.1 policy those modules are **not bundled**; whenever they are needed they are loaded
from a pinned, git-ignored checkout produced by ``scripts/fetch_official_starter.py``.

This package keeps the repository's offline/default test surface free of any third-party
code while still allowing strongly-separated, optional reproducibility checks.
"""

from __future__ import annotations

__all__: list[str] = []