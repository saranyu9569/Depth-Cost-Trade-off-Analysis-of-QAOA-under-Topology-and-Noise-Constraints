from __future__ import annotations

from qiskit import transpile
from qiskit.transpiler import CouplingMap

BASIS_GATES = ["rz", "sx", "x", "cx"]
MEASUREMENT_BASIS_GATES = ["rz", "sx", "x", "cx", "measure"]


def _both_directions(edges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(set(edges + [(b, a) for a, b in edges]))


def coupling_map_for_topology(topology: str, n: int) -> CouplingMap | None:
    if topology == "all_to_all":
        return None

    if topology == "linear":
        edges = [(i, i + 1) for i in range(n - 1)]
        return CouplingMap(_both_directions(edges))

    if topology == "ring":
        edges = [(i, i + 1) for i in range(n - 1)]
        if n > 2:
            edges.append((n - 1, 0))
        return CouplingMap(_both_directions(edges))

    if topology == "grid":
        # Compact 2D grid-like topology for n qubits.
        import math
        cols = int(math.ceil(math.sqrt(n)))
        edges: list[tuple[int, int]] = []
        for q in range(n):
            right = q + 1
            down = q + cols
            if right < n and (q // cols) == (right // cols):
                edges.append((q, right))
            if down < n:
                edges.append((q, down))
        return CouplingMap(_both_directions(edges))

    if topology == "heavy_hex_like":
        # Lightweight heavy-hex-inspired sparse topology.
        # This is NOT an IBM backend replica; it is a sparse connectivity proxy.
        edges = [(i, i + 1) for i in range(n - 1)]
        for i in range(0, n - 2, 3):
            edges.append((i, i + 2))
        for i in range(1, n - 3, 4):
            edges.append((i, i + 3))
        return CouplingMap(_both_directions(edges))

    raise ValueError(f"Unknown topology: {topology}")


def transpiled_metrics(qc, topology: str, n: int, optimization_level: int, seed: int) -> dict[str, float | str]:
    cmap = coupling_map_for_topology(topology, n)
    tqc = transpile(
        qc,
        basis_gates=BASIS_GATES,
        coupling_map=cmap,
        optimization_level=optimization_level,
        seed_transpiler=seed,
    )
    ops = tqc.count_ops()
    cx = int(ops.get("cx", 0))
    oneq = int(sum(int(ops.get(g, 0)) for g in ["rz", "sx", "x"] ))
    return {
        "topology": topology,
        "transpiled_depth": int(tqc.depth()),
        "transpiled_cx": cx,
        "transpiled_1q_ops": oneq,
        "transpiled_total_ops": int(sum(ops.values())),
    }
