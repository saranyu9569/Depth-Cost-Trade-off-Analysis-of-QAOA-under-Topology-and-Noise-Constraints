from __future__ import annotations

import networkx as nx
import numpy as np


def generate_graph(graph_type: str, n: int, seed: int) -> nx.Graph:
    if graph_type == "erdos_renyi":
        # Moderately dense enough to make Max-Cut non-trivial on small n.
        p = min(0.35 + 0.02 * (n / 2), 0.65)
        g = nx.erdos_renyi_graph(n, p, seed=seed)
        if not nx.is_connected(g):
            # Use deterministic completion to avoid disconnected trivial cases.
            components = [list(c) for c in nx.connected_components(g)]
            for a, b in zip(components[:-1], components[1:]):
                g.add_edge(a[0], b[0])
        return nx.convert_node_labels_to_integers(g)

    if graph_type == "random_regular":
        d = 3 if n > 4 else 2
        if (n * d) % 2 != 0:
            d = 2
        return nx.random_regular_graph(d, n, seed=seed)

    if graph_type == "watts_strogatz":
        k = 4 if n >= 6 else 2
        return nx.watts_strogatz_graph(n, k, 0.30, seed=seed)

    raise ValueError(f"Unknown graph_type: {graph_type}")


def graph_features(g: nx.Graph) -> dict[str, float]:
    degrees = np.array([d for _, d in g.degree()], dtype=float)
    n = g.number_of_nodes()
    m = g.number_of_edges()
    return {
        "num_nodes": int(n),
        "num_edges": int(m),
        "edge_density": float(nx.density(g)),
        "avg_degree": float(degrees.mean()) if len(degrees) else 0.0,
        "degree_std": float(degrees.std()) if len(degrees) else 0.0,
        "max_degree": int(degrees.max()) if len(degrees) else 0,
        "clustering": float(nx.average_clustering(g)) if n > 1 else 0.0,
    }
