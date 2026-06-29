from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
import networkx as nx

from .circuit import build_qaoa_circuit
from .evaluator import evaluate_exact


def random_theta(p: int, bounds: dict, rng: np.random.Generator) -> np.ndarray:
    g_lo, g_hi = bounds["gamma"]
    b_lo, b_hi = bounds["beta"]
    vals = []
    for _ in range(p):
        vals.append(rng.uniform(g_lo, g_hi))
        vals.append(rng.uniform(b_lo, b_hi))
    return np.array(vals, dtype=float)


def clip_theta(theta: np.ndarray, p: int, bounds: dict) -> np.ndarray:
    theta = np.asarray(theta, dtype=float).copy()
    g_lo, g_hi = bounds["gamma"]
    b_lo, b_hi = bounds["beta"]
    for i in range(p):
        theta[2*i] = np.clip(theta[2*i], g_lo, g_hi)
        theta[2*i+1] = np.clip(theta[2*i+1], b_lo, b_hi)
    return theta


def optimize_qaoa(
    g: nx.Graph,
    p: int,
    optimizer: str,
    bounds: dict,
    optimal_cut: int,
    optimal_bitstrings: list[str],
    seed: int,
    cobyla_maxiter: int,
    spsa_iterations: int,
) -> tuple[np.ndarray, dict[str, float], list[dict[str, float]]]:
    rng = np.random.default_rng(seed)
    theta0 = random_theta(p, bounds, rng)
    trajectory: list[dict[str, float]] = []
    eval_id = 0

    def objective(theta: np.ndarray) -> float:
        nonlocal eval_id
        theta = clip_theta(np.asarray(theta, dtype=float), p, bounds)
        qc = build_qaoa_circuit(g, theta, p)
        result = evaluate_exact(g, qc, optimal_cut, optimal_bitstrings)
        ratio = float(result["exact_expected_ratio"])
        trajectory.append({
            "evaluation_id": eval_id,
            "objective": -ratio,
            "exact_expected_ratio": ratio,
            **{f"theta_{i}": float(x) for i, x in enumerate(theta)},
        })
        eval_id += 1
        return -ratio

    opt = optimizer.upper()
    if opt == "COBYLA":
        res = minimize(objective, theta0, method="COBYLA", options={"maxiter": int(cobyla_maxiter), "rhobeg": 0.4})
        theta_best = clip_theta(res.x, p, bounds)

    elif opt == "SPSA":
        theta = theta0.copy()
        best_theta = theta.copy()
        best_val = objective(theta)
        a = 0.25
        c = 0.10
        alpha = 0.602
        gamma = 0.101
        for k in range(1, int(spsa_iterations) + 1):
            ak = a / (k ** alpha)
            ck = c / (k ** gamma)
            delta = rng.choice([-1.0, 1.0], size=theta.shape)
            y_plus = objective(theta + ck * delta)
            y_minus = objective(theta - ck * delta)
            ghat = (y_plus - y_minus) / (2.0 * ck * delta)
            theta = clip_theta(theta - ak * ghat, p, bounds)
            val = objective(theta)
            if val < best_val:
                best_val = val
                best_theta = theta.copy()
        theta_best = best_theta

    else:
        raise ValueError(f"Unsupported optimizer: {optimizer}")

    qc = build_qaoa_circuit(g, theta_best, p)
    final = evaluate_exact(g, qc, optimal_cut, optimal_bitstrings)
    final_metrics = {
        "final_objective": -float(final["exact_expected_ratio"]),
        "num_function_evaluations": len(trajectory),
    }
    return theta_best, final_metrics, trajectory
