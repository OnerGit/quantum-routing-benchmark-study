"""Adapters for building A3-compatible inputs and loading official benchmark records.

The frozen A3 ``solve`` accepts a NetworkX simple undirected graph with ordinary integer
labels and a program given as a list of ``("1Q", q)`` / ``("2Q", a, b)`` tuples. This module
provides small helpers used by the repository tests and the reproducibility docs.

Nothing here wraps or bundles any third-party solver; it only constructs plain test inputs.
"""

from __future__ import annotations

from typing import Iterable

import networkx as nx


def path_hardware(num_qubits: int) -> nx.Graph:
    """Return a connected path graph on ``num_qubits`` integer labels (0..n-1)."""
    if num_qubits < 1:
        raise ValueError("num_qubits must be >= 1")
    g = nx.Graph()
    g.add_nodes_from(range(num_qubits))
    for i in range(num_qubits - 1):
        g.add_edge(i, i + 1)
    return g


def nearest_neighbor_program(num_qubits: int, layers: int = 2) -> list[tuple]:
    """A simple deterministic layered CNOT-chain program (all-local, no SWAP expected)."""
    ops: list[tuple] = []
    for _ in range(layers):
        for i in range(0, num_qubits - 1, 2):
            ops.append(("2Q", i, i + 1))
        for i in range(1, num_qubits - 1, 2):
            ops.append(("2Q", i, i + 1))
    return ops


def crossing_program(blocked_pair: tuple[int, int], size: int = 4) -> list[tuple]:
    """Deterministic program whose logical pair is stuck two hops away (forces SWAPs).

    ``blocked_pair`` must be ``(a, b)`` with ``a`` and ``b`` not adjacent on the path host.
    """
    a, b = blocked_pair
    if a == b or abs(a - b) == 1:
        raise ValueError("blocked_pair must be non-adjacent on the path host")
    ops: list[tuple] = [("2Q", a, b)]
    for i in range(0, size - 1, 2):
        ops.append(("2Q", i, i + 1))
    return ops


def normalize_program(program: Iterable[tuple]) -> list[tuple]:
    """Return a plain list of tuple ops (the frozen solver requires tuple ops in a list)."""
    out = []
    for op in program:
        if not isinstance(op, tuple):
            raise TypeError("each op must be a tuple")
        out.append(op)
    return out