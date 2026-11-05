"""Deterministic bidirectional placement with frozen strict-progress routing."""
from dataclasses import dataclass
from types import MappingProxyType
import networkx as nx
import placement
import routing

ARCHITECTURE_ID = "OC-V2-A3-BIDIRECTIONAL-20260921"
STATIC_SEED_COUNT = 2
MAX_DISTINCT_PLACEMENTS = 4
FROZEN_PARAMETERS = MappingProxyType({
    "placement_seed_policy": "interaction-driven greedy + sorted-rank",
    "placement_weight": "2Q occurrence frequency", "placement_normalization": "none",
    "placement_refinement_policy": "strict full best improvement, exchange/empty relocation",
    "placement_scan_cap": placement.SCAN_CAP, "static_seed_count": STATIC_SEED_COUNT,
    "max_distinct_placements": MAX_DISTINCT_PLACEMENTS,
    "feedback_cycles_per_seed": 1, "feedback_refinement": False,
    "lookahead_window": routing.LOOKAHEAD_WINDOW, "temporal_discount": 1,
    "future_distance_weight": 1, "future_normalization": "actual future count; zero if empty",
    "depth_weight": 0.5, "decay": False, "randomness": "none",
    "routing_progress": "d_after = d_before - 1", "final_objective": "2 * swaps + depth",
})


@dataclass(frozen=True)
class Context:
    nodes: tuple
    logicals: tuple
    neighbors: object
    distances: object
    edges: tuple


def prepare(program, hardware_graph):
    if not isinstance(hardware_graph, nx.Graph) or hardware_graph.is_directed() or hardware_graph.is_multigraph():
        raise ValueError("hardware must be a simple undirected NetworkX graph")
    if not hardware_graph or any(type(v) is not int for v in hardware_graph):
        raise ValueError("hardware must be nonempty with ordinary integer labels")
    if nx.number_of_selfloops(hardware_graph) or not nx.is_connected(hardware_graph):
        raise ValueError("hardware must be connected and have no self-loops")
    if type(program) is not list:
        raise ValueError("program must be a list of exact operation tuples")
    for op in program:
        if (type(op) is not tuple or not op or type(op[0]) is not str or
                op[0] not in ("1Q", "2Q") or len(op) != (2 if op[0] == "1Q" else 3) or
                any(type(q) is not int for q in op[1:]) or
                (op[0] == "2Q" and op[1] == op[2])):
            raise ValueError("operation outside frozen 1Q/2Q integer domain")
    logicals = tuple(sorted({q for op in program for q in op[1:]}))
    nodes = tuple(sorted(hardware_graph))
    if len(logicals) > len(nodes):
        raise ValueError("more logical qubits than physical sites")
    neighbors = MappingProxyType({v: tuple(sorted(hardware_graph.neighbors(v))) for v in nodes})
    raw = dict(nx.all_pairs_shortest_path_length(hardware_graph))
    distances = MappingProxyType({v: MappingProxyType({u: raw[v][u] for u in nodes}) for v in nodes})
    edges = tuple(sorted(tuple(sorted(e)) for e in hardware_graph.edges))
    return tuple(program), Context(nodes, logicals, neighbors, distances, edges)


def trial_key(trial, logicals):
    return (2 * trial.swap_count + trial.depth,
            tuple(trial.initial_placement[a] for a in logicals), trial.routed_program)


def _final_mapping(initial, routed):
    """Recover the final logical placement by replaying SWAP token exchanges."""
    live = dict(initial)
    for op in routed:
        if op[0] == "SWAP":
            _, u, v = op
            live = {q: (v if p == u else u if p == v else p) for q, p in live.items()}
    return live


def solve(program, hardware_graph):
    """Return the initial placement and routed ORIGINAL program, deterministically."""
    frozen, ctx = prepare(program, hardware_graph)
    if not frozen:
        return {}, []
    weights = placement.interaction_weights(frozen)
    raw_seeds = (placement.greedy_seed(ctx, weights), placement.rank_seed(ctx))
    refined_cache, seeds = {}, []
    for seed in raw_seeds:
        key = tuple(seed[q] for q in ctx.logicals)
        if key not in refined_cache:
            refined_cache[key] = placement.refine(seed, ctx, weights)[0]
        seeds.append(dict(refined_cache[key]))

    trials, by_layout = [], {}
    def add(initial):
        key = tuple(initial[q] for q in ctx.logicals)
        if key not in by_layout:
            trial = routing.route(frozen, ctx, initial)
            by_layout[key] = trial
            trials.append(trial)
        return by_layout[key]

    static_trials = [add(seed) for seed in seeds]
    backward_program = tuple(reversed(frozen))
    feedback_layouts = []
    for seed, forward in zip(seeds, static_trials):
        final_forward = _final_mapping(seed, forward.routed_program)
        placement.check_layout(final_forward, ctx)
        backward = routing.route(backward_program, ctx, final_forward)
        feedback = _final_mapping(final_forward, backward.routed_program)
        placement.check_layout(feedback, ctx)
        feedback_layouts.append(feedback)
    # Feedback layouts are never refined. Keep all original static candidates.
    for feedback in feedback_layouts:
        add(feedback)
    routing.require(1 <= len(trials) <= MAX_DISTINCT_PLACEMENTS, "trial count invariant failed")
    winner = min(trials, key=lambda trial: trial_key(trial, ctx.logicals))
    return dict(winner.initial_placement), list(winner.routed_program)
