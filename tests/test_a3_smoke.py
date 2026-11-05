"""A3 smoke, output-contract, and determinism tests on synthetic hardware."""

from __future__ import annotations

import networkx as nx

from routing_study.a3 import solve, prepare
from routing_study.adapters.inputs import (
    crossing_program,
    nearest_neighbor_program,
    path_hardware,
)


def _assert_valid_output(placement, routed, graph, program):
    logicals = sorted({q for op in program for q in op[1:]})
    assert isinstance(placement, dict)
    assert set(placement) == set(logicals)
    values = list(placement.values())
    assert len(set(values)) == len(values), "placement not injective"
    assert set(values).issubset(set(graph.nodes))
    # routed program occupies physical labels; validate edge/occupancy contract.
    occupied = set(placement.values())
    for op in routed:
        assert op[0] in ("1Q", "2Q", "SWAP")
        assert all(isinstance(x, int) for x in op[1:])
        if op[0] == "SWAP":
            _, u, v = op
            assert graph.has_edge(u, v), f"SWAP on non-edge {(u, v)}"
        elif op[0] == "2Q":
            _, u, v = op
            assert graph.has_edge(u, v), f"2Q on non-edge {(u, v)}"


def test_empty_program_returns_empty():
    g = path_hardware(4)
    placement, routed = solve([], g)
    assert placement == {}
    assert list(routed) == []


def test_smoke_path_and_triangle():
    g = path_hardware(5)
    prog = [("2Q", 0, 1), ("2Q", 1, 2), ("2Q", 2, 0)]
    placement, routed = solve(list(prog), g)
    _assert_valid_output(placement, routed, g, prog)
    swaps = sum(1 for op in routed if op[0] == "SWAP")
    assert swaps >= 1, "triangle on a path should require at least one SWAP"


def test_nearest_neighbor_no_gate_invalid():
    g = path_hardware(6)
    prog = nearest_neighbor_program(6, layers=2)
    placement, routed = solve(list(prog), g)
    _assert_valid_output(placement, routed, g, prog)


def test_determinism():
    g = path_hardware(6)
    prog = [("2Q", 0, 1), ("2Q", 1, 2), ("2Q", 2, 0), ("2Q", 0, 3), ("2Q", 3, 4)]
    a = solve(list(prog), g)
    b = solve(list(prog), g)
    assert a == b


def test_output_contract_types():
    g = path_hardware(5)
    prog = [("2Q", 0, 4), ("2Q", 4, 1)]
    p, r = solve(list(prog), g)
    assert isinstance(p, dict)
    assert isinstance(r, list)
    assert all(isinstance(op, tuple) for op in r)


def test_prepare_validates_bad_hardware():
    g = nx.DiGraph()
    g.add_nodes_from([0, 1, 2])
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    with __import__("pytest").raises(ValueError):
        prepare([("2Q", 0, 1)], g)


def test_prepare_validates_bad_program():
    g = path_hardware(4)
    bad_programs = [1, [("3Q", 0, 1, 2)], [("2Q", 0, 0)], [("2Q", "a", 1)]]
    for bad in bad_programs:
        with __import__("pytest").raises(ValueError):
            prepare(bad, g)


def test_prepare_returns_context_contract():
    g = path_hardware(4)
    frozen, ctx = prepare([("2Q", 0, 2)], g)
    assert isinstance(frozen, tuple)
    from types import MappingProxyType

    assert isinstance(ctx.nodes, tuple)
    assert isinstance(ctx.logicals, tuple)
    assert isinstance(ctx.neighbors, MappingProxyType)
    assert isinstance(ctx.distances, MappingProxyType)
    assert isinstance(ctx.edges, tuple)


def test_crossing_program_never_reports_empty():
    g = path_hardware(7)
    prog = crossing_program((0, 6), size=7)
    placement, routed = solve(list(prog), g)
    assert list(routed)