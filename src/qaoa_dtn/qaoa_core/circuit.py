from __future__ import annotations

from qiskit import QuantumCircuit
import networkx as nx
import numpy as np


def split_theta(theta: np.ndarray | list[float], p: int) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(theta, dtype=float)
    if arr.size != 2 * p:
        raise ValueError(f"Expected theta length {2*p}, got {arr.size}")
    gammas = arr[0::2]
    betas = arr[1::2]
    return gammas, betas


def build_qaoa_circuit(g: nx.Graph, theta: np.ndarray | list[float], p: int) -> QuantumCircuit:
    """Build a QAOA circuit for unweighted Max-Cut.

    Parameter convention:
    theta = [gamma_1, beta_1, gamma_2, beta_2, ...].
    Cost layer uses CX-RZ-CX implementation per graph edge.
    Mixer layer uses RX rotations.
    """
    n = g.number_of_nodes()
    gammas, betas = split_theta(theta, p)
    qc = QuantumCircuit(n)
    qc.h(range(n))

    for layer in range(p):
        gamma = float(gammas[layer])
        beta = float(betas[layer])
        for u, v in g.edges():
            qc.cx(u, v)
            qc.rz(2.0 * gamma, v)
            qc.cx(u, v)
        for q in range(n):
            qc.rx(2.0 * beta, q)
    return qc


def add_measurements(qc: QuantumCircuit) -> QuantumCircuit:
    measured = qc.copy()
    measured.measure_all()
    return measured
