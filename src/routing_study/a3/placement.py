"""Frozen OC-V1-A2 placement: frequency objective, two seeds, bounded refinement."""
from itertools import combinations

SCAN_CAP = 16


def interaction_weights(program):
    weights = {}
    for op in program:
        if op[0] == "2Q":
            pair = tuple(sorted(op[1:]))
            weights[pair] = weights.get(pair, 0) + 1
    return dict(sorted(weights.items()))


def objective(mapping, weights, distances):
    return sum(w * distances[mapping[a]][mapping[b]] for (a, b), w in weights.items())


def greedy_seed(ctx, weights):
    def weight(a, b):
        return weights.get((min(a, b), max(a, b)), 0)

    wd = {a: sum(weight(a, b) for b in ctx.logicals) for a in ctx.logicals}
    ud = {a: sum(weight(a, b) > 0 for b in ctx.logicals) for a in ctx.logicals}
    far = {v: sum(ctx.distances[v].values()) for v in ctx.nodes}
    mapping = {}
    unused = set(ctx.nodes)
    while len(mapping) < len(ctx.logicals):
        a = min((a for a in ctx.logicals if a not in mapping), key=lambda a: (
            -sum(weight(a, b) for b in mapping), -wd[a], -ud[a], a))
        v = min(sorted(unused), key=lambda v: (
            sum(weight(a, b) * ctx.distances[v][mapping[b]] for b in mapping),
            -len(ctx.neighbors[v]), far[v], v))
        mapping[a] = v
        unused.remove(v)
    return mapping


def rank_seed(ctx):
    return dict(zip(ctx.logicals, ctx.nodes))


def check_layout(mapping, ctx):
    if (set(mapping) != set(ctx.logicals) or len(set(mapping.values())) != len(mapping)
            or not set(mapping.values()).issubset(ctx.nodes)):
        raise RuntimeError("placement injection/coverage invariant failed")


def refine(seed, ctx, weights):
    """Return layout and passive full-scan diagnostics; no runtime SWAPs."""
    mapping = dict(seed)
    check_layout(mapping, ctx)
    cost = objective(mapping, weights, ctx.distances)
    history = []
    for scan in range(1, SCAN_CAP + 1):
        occupied = {p: q for q, p in mapping.items()}
        best = None
        best_mapping = None
        evaluated = 0
        for u, v in combinations(ctx.nodes, 2):
            if u not in occupied and v not in occupied:
                continue
            trial = dict(mapping)
            if u in occupied:
                trial[occupied[u]] = v
            if v in occupied:
                trial[occupied[v]] = u
            key = (objective(trial, weights, ctx.distances), u, v)
            evaluated += 1
            if best is None or key < best:
                best, best_mapping = key, trial
        accepted = best is not None and best[0] < cost
        history.append({"scan": scan, "before": dict(mapping), "before_cost": cost,
                        "best_key": best, "evaluated": evaluated, "accepted": accepted})
        if not accepted:
            break
        mapping, cost = best_mapping, best[0]
        check_layout(mapping, ctx)
    return mapping, history
