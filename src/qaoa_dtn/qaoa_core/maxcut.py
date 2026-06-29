from __future__ import annotations

import itertools
import networkx as nx


def cut_value(g: nx.Graph, bits: str) -> int:
    """Compute the Max-Cut value for a bitstring ordered by node index 0..n-1."""
    return int(sum(1 for u, v in g.edges() if bits[u] != bits[v]))


def brute_force_maxcut(g: nx.Graph) -> tuple[int, list[str]]:
    n = g.number_of_nodes()
    best = -1
    best_bits: list[str] = []
    for tup in itertools.product("01", repeat=n):
        bits = "".join(tup)
        val = cut_value(g, bits)
        if val > best:
            best = val
            best_bits = [bits]
        elif val == best:
            best_bits.append(bits)
    return best, best_bits


def random_bitstring_baseline(g: nx.Graph, seed: int, n_samples: int) -> dict[str, float]:
    import numpy as np

    rng = np.random.default_rng(seed)
    n = g.number_of_nodes()
    values = []
    for _ in range(n_samples):
        bits = "".join(str(int(x)) for x in rng.integers(0, 2, size=n))
        values.append(cut_value(g, bits))
    return {
        "random_mean_cut": float(np.mean(values)),
        "random_best_cut": float(np.max(values)),
    }


def greedy_maxcut_baseline(g: nx.Graph, seed: int = 0) -> dict[str, float | str]:
    # Deterministic greedy local improvement with seeded random initialization.
    import numpy as np

    rng = np.random.default_rng(seed)
    n = g.number_of_nodes()
    assignment = rng.integers(0, 2, size=n).astype(int)

    improved = True
    while improved:
        improved = False
        order = list(range(n))
        rng.shuffle(order)
        for node in order:
            current = assignment.copy()
            flipped = assignment.copy()
            flipped[node] = 1 - flipped[node]
            cur_bits = "".join(str(x) for x in current)
            flip_bits = "".join(str(x) for x in flipped)
            if cut_value(g, flip_bits) > cut_value(g, cur_bits):
                assignment = flipped
                improved = True

    bits = "".join(str(x) for x in assignment)
    return {"greedy_cut": float(cut_value(g, bits)), "greedy_bits": bits}
