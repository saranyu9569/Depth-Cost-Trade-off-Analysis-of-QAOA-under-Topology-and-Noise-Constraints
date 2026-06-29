from __future__ import annotations

from collections import Counter
from typing import Mapping
import numpy as np
import networkx as nx
from qiskit.quantum_info import Statevector
from qiskit import transpile

from .circuit import add_measurements
from .maxcut import cut_value


def _qiskit_key_to_node_bits(key: str) -> str:
    # Qiskit count/probability keys are displayed as q_{n-1}...q_0.
    return key.replace(" ", "")[::-1]


def exact_probabilities(qc) -> dict[str, float]:
    sv = Statevector.from_instruction(qc)
    raw = sv.probabilities_dict()
    return {_qiskit_key_to_node_bits(k): float(v) for k, v in raw.items()}


def evaluate_distribution(
    g: nx.Graph,
    probs_or_counts: Mapping[str, float | int],
    optimal_cut: int,
    optimal_bitstrings: list[str],
    is_counts: bool = False,
) -> dict[str, float | str]:
    if is_counts:
        total = float(sum(float(v) for v in probs_or_counts.values()))
        probs = {str(k): float(v) / total for k, v in probs_or_counts.items()} if total > 0 else {}
    else:
        probs = {str(k): float(v) for k, v in probs_or_counts.items()}

    expected_cut = 0.0
    best_cut = -1
    best_bits = ""
    optimal_prob = 0.0
    opt_set = set(optimal_bitstrings)

    for bits, p in probs.items():
        node_bits = bits if len(bits) == g.number_of_nodes() else _qiskit_key_to_node_bits(bits)
        val = cut_value(g, node_bits)
        expected_cut += p * val
        if val > best_cut:
            best_cut = val
            best_bits = node_bits
        if node_bits in opt_set:
            optimal_prob += p

    ratio = expected_cut / optimal_cut if optimal_cut > 0 else 0.0
    best_ratio = best_cut / optimal_cut if optimal_cut > 0 else 0.0
    return {
        "expected_cut": float(expected_cut),
        "exact_expected_ratio" if not is_counts else "empirical_expected_ratio": float(ratio),
        "best_cut": float(best_cut),
        "best_ratio": float(best_ratio),
        "best_bitstring": best_bits,
        "optimal_solution_probability": float(optimal_prob),
    }


def evaluate_exact(g: nx.Graph, qc, optimal_cut: int, optimal_bitstrings: list[str]) -> dict[str, float | str]:
    probs = exact_probabilities(qc)
    return evaluate_distribution(g, probs, optimal_cut, optimal_bitstrings, is_counts=False)


def sample_from_exact(
    g: nx.Graph,
    qc,
    optimal_cut: int,
    optimal_bitstrings: list[str],
    shots: int,
    seed: int,
) -> dict[str, float | str]:
    probs = exact_probabilities(qc)
    keys = list(probs.keys())
    pvals = np.array([probs[k] for k in keys], dtype=float)
    pvals = pvals / pvals.sum()
    rng = np.random.default_rng(seed)
    samples = rng.choice(keys, size=shots, p=pvals)
    counts = Counter(samples)
    return evaluate_distribution(g, counts, optimal_cut, optimal_bitstrings, is_counts=True)


def evaluate_noisy_counts(
    g: nx.Graph,
    qc,
    simulator,
    coupling_map,
    basis_gates: list[str],
    optimization_level: int,
    shots: int,
    seed: int,
    optimal_cut: int,
    optimal_bitstrings: list[str],
) -> dict[str, float | str]:
    measured = add_measurements(qc)
    # Critical compatibility rule: do not pass backend into transpile here.
    # Passing backend+basis_gates+coupling_map can trigger qiskit errors when
    # simulator basis contains 3-qubit gates. We explicitly specify a simple basis.
    tqc = transpile(
        measured,
        basis_gates=basis_gates,
        coupling_map=coupling_map,
        optimization_level=optimization_level,
        seed_transpiler=seed,
    )
    result = simulator.run(tqc, shots=shots, seed_simulator=seed).result()
    raw_counts = result.get_counts()
    counts = {_qiskit_key_to_node_bits(k): int(v) for k, v in raw_counts.items()}
    return evaluate_distribution(g, counts, optimal_cut, optimal_bitstrings, is_counts=True)
