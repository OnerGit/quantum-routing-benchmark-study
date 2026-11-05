"""Strict-order, strict-progress routing with private candidate evaluation."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import NamedTuple

_EMPTY = object()
LOOKAHEAD_WINDOW = 8


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Candidate(NamedTuple):
    cost: int
    distance_after: int
    u: int
    v: int
    layer: int
    delta_depth: int

    @property
    def key(self):
        return self[:4]


class MappingState:
    def __init__(self, initial, ctx):
        self.ctx = ctx
        self.initial_placement = MappingProxyType(dict(initial))
        self.logical_to_physical = dict(initial)
        self.physical_to_logical = {v: _EMPTY for v in ctx.nodes}
        for q, p in initial.items():
            self.physical_to_logical[p] = q
        self.routed_program = []
        self.qubit_last_layer = {v: 0 for v in ctx.nodes}
        self.current_depth = 0
        self.swap_count = 0
        self.original_cursor = 0
        self.two_q_index = 0
        self.check()

    def check(self):
        m, occ = self.logical_to_physical, self.physical_to_logical
        require(set(m) == set(self.ctx.logicals), "live logical coverage failed")
        require(set(occ) == set(self.ctx.nodes), "physical coverage failed")
        require(len(set(m.values())) == len(m), "live injection failed")
        tokens = [q for q in occ.values() if q is not _EMPTY]
        require(len(tokens) == len(m) and set(tokens) == set(m), "occupancy failed")
        require(all(occ.get(p, _EMPTY) == q for q, p in m.items()), "inverse maps failed")

    def projected_layer(self, u, v):
        layer = 1 + max(self.qubit_last_layer[u], self.qubit_last_layer[v])
        return layer, max(0, layer - self.current_depth)

    def update_layers(self, u, v):
        layer, _ = self.projected_layer(u, v)
        self.qubit_last_layer[u] = self.qubit_last_layer[v] = layer
        self.current_depth = max(self.current_depth, layer)

    def swap_tokens(self, u, v):
        """State primitive, also coherent for EMPTY/EMPTY; no layer mutation."""
        x, y = self.physical_to_logical[u], self.physical_to_logical[v]
        self.physical_to_logical[u], self.physical_to_logical[v] = y, x
        if x is not _EMPTY:
            self.logical_to_physical[x] = v
        if y is not _EMPTY:
            self.logical_to_physical[y] = u
        self.check()

    def commit_swap(self, u, v, a, b):
        require(u < v and (u, v) in self.ctx.edges, "SWAP edge/canonical invariant failed")
        require(self.logical_to_physical[a] in (u, v) or
                self.logical_to_physical[b] in (u, v), "SWAP must touch current operand")
        self.swap_tokens(u, v)
        self.routed_program.append(("SWAP", u, v))
        self.swap_count += 1
        self.update_layers(u, v)

    def emit_one(self, a):
        self.routed_program.append(("1Q", self.logical_to_physical[a]))
        self.original_cursor += 1


def evaluate_candidate(state, u, v, a, b, future):
    mapping = dict(state.logical_to_physical)
    x, y = state.physical_to_logical[u], state.physical_to_logical[v]
    if x is not _EMPTY:
        mapping[x] = v
    if y is not _EMPTY:
        mapping[y] = u
    distances = state.ctx.distances
    after = distances[mapping[a]][mapping[b]]
    total = sum(distances[mapping[c]][mapping[e]] for _, c, e in future)
    layer, delta = state.projected_layer(u, v)
    require(delta in (0, 1), "candidate depth increment invariant failed")
    return Candidate(2 * total + max(1, len(future)) * delta, after, u, v, layer, delta)


def reducing_candidates(state, a, b, future):
    p, q = state.logical_to_physical[a], state.logical_to_physical[b]
    before = state.ctx.distances[p][q]
    require(before > 1, "candidate generation requires blocked gate")
    edges = sorted({tuple(sorted((x, y))) for x in (p, q) for y in state.ctx.neighbors[x]})
    candidates = []
    for u, v in edges:
        candidate = evaluate_candidate(state, u, v, a, b, future)
        if candidate.distance_after < before:
            require(candidate.distance_after == before - 1, "strict progress failed in evaluation")
            candidates.append(candidate)
    require(bool(candidates), f"no reducing candidate for logical pair {(a, b)} at {(p, q)}")
    return candidates, len(edges)


@dataclass(frozen=True)
class RouteResult:
    initial_placement: object
    routed_program: tuple
    swap_count: int
    depth: int
    gates: tuple
    candidate_evaluations: int
    retained_candidates: int


def route(program, ctx, initial):
    state = MappingState(initial, ctx)
    occurrences = tuple(op for op in program if op[0] == "2Q")
    gates = []
    evaluated = retained = 0
    for op in program:
        if op[0] == "1Q":
            state.emit_one(op[1])
            continue
        _, a, b = op
        m = state.logical_to_physical
        distance = ctx.distances[m[a]][m[b]]
        sequence = [distance]
        future = occurrences[state.two_q_index + 1:state.two_q_index + 1 + LOOKAHEAD_WINDOW]
        gate_evaluations = 0
        while distance > 1:
            candidates, count = reducing_candidates(state, a, b, future)
            evaluated += count
            gate_evaluations += count
            retained += len(candidates)
            chosen = min(candidates, key=lambda c: c.key)
            state.commit_swap(chosen.u, chosen.v, a, b)
            new_distance = ctx.distances[m[a]][m[b]]
            require(new_distance == distance - 1, "strict progress failed after commit")
            distance = new_distance
            sequence.append(distance)
        p, q = m[a], m[b]
        require(q in ctx.neighbors[p] and p != q, "2Q adjacency failed")
        require(state.physical_to_logical[p] == a and state.physical_to_logical[q] == b,
                "ordered operand occupancy failed")
        require(len(sequence) - 1 == sequence[0] - 1, "gate SWAP bound failed")
        state.routed_program.append(("2Q", p, q))
        state.update_layers(p, q)
        gates.append({"original_index": state.original_cursor, "two_q_index": state.two_q_index,
                      "distance_sequence": tuple(sequence), "future": future,
                      "candidate_evaluations": gate_evaluations})
        state.two_q_index += 1
        state.original_cursor += 1
    require(state.original_cursor == len(program), "original cursor failed")
    require(dict(state.initial_placement) == initial, "initial snapshot changed")
    state.check()
    return RouteResult(state.initial_placement, tuple(state.routed_program), state.swap_count,
                       state.current_depth, tuple(gates), evaluated, retained)
