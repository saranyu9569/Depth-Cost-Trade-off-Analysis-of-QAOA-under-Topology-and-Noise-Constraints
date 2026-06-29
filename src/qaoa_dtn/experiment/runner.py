from __future__ import annotations

from pathlib import Path
import time
import platform
import pandas as pd
from tqdm import tqdm

from qaoa_dtn.qaoa_core.graphs import generate_graph, graph_features
from qaoa_dtn.qaoa_core.maxcut import brute_force_maxcut, random_bitstring_baseline, greedy_maxcut_baseline
from qaoa_dtn.qaoa_core.circuit import build_qaoa_circuit
from qaoa_dtn.qaoa_core.evaluator import evaluate_exact, sample_from_exact, evaluate_noisy_counts
from qaoa_dtn.qaoa_core.hardware import transpiled_metrics, coupling_map_for_topology, MEASUREMENT_BASIS_GATES
from qaoa_dtn.qaoa_core.noise import NoiseSetting, build_aer_simulator
from qaoa_dtn.qaoa_core.optimizers import optimize_qaoa
from qaoa_dtn.analysis.tables import make_summaries
from qaoa_dtn.analysis.plots import make_figures
from qaoa_dtn.utils.io import ensure_dir, save_csv, save_json


def _graph_id(graph_type: str, n: int, seed: int) -> str:
    return f"{graph_type}_n{n}_s{seed}"


def run_experiment(cfg: dict) -> dict[str, str]:
    name = cfg["experiment"]["name"]
    seed0 = int(cfg["experiment"].get("random_seed", 42))
    output_dir = ensure_dir(cfg["experiment"]["output_dir"])
    figure_dir = ensure_dir(cfg["experiment"]["figure_dir"])
    primary_topology = cfg["experiment"].get("primary_topology", "linear")

    graph_types = cfg["graphs"]["graph_types"]
    sizes = [int(x) for x in cfg["graphs"]["num_nodes"]]
    graph_seeds = [int(x) for x in cfg["graphs"]["graph_seeds"]]
    depths = [int(x) for x in cfg["qaoa"]["depths"]]
    optimizers = cfg["qaoa"]["optimizers"]
    bounds = cfg["qaoa"]["parameter_bounds"]
    shots = int(cfg["qaoa"].get("shots", 2048))
    cobyla_maxiter = int(cfg["qaoa"].get("cobyla_maxiter", 70))
    spsa_iterations = int(cfg["qaoa"].get("spsa_iterations", 60))
    topologies = cfg["topologies"]["names"]
    transpile_level = int(cfg["topologies"].get("optimization_level", 3))

    instances = [(gt, n, gs) for gt in graph_types for n in sizes for gs in graph_seeds]

    qaoa_rows = []
    topology_rows = []
    noise_rows = []
    trajectory_rows = []
    baseline_rows = []

    start = time.time()

    for instance_idx, (gt, n, gseed) in enumerate(tqdm(instances, desc="Graph instances")):
        g = generate_graph(gt, n, gseed)
        gid = _graph_id(gt, n, gseed)
        feats = graph_features(g)
        optimal_cut, optimal_bitstrings = brute_force_maxcut(g)

        rand_base = random_bitstring_baseline(g, seed0 + gseed, n_samples=shots)
        greedy_base = greedy_maxcut_baseline(g, seed0 + gseed)
        baseline_rows.append({
            "graph_id": gid,
            "graph_type": gt,
            "graph_seed": gseed,
            **feats,
            "optimal_cut": optimal_cut,
            **rand_base,
            "random_mean_ratio": rand_base["random_mean_cut"] / optimal_cut if optimal_cut else 0.0,
            "random_best_ratio": rand_base["random_best_cut"] / optimal_cut if optimal_cut else 0.0,
            **greedy_base,
            "greedy_ratio": greedy_base["greedy_cut"] / optimal_cut if optimal_cut else 0.0,
        })

        for p in depths:
            for opt in optimizers:
                run_seed = seed0 + 1000 * instance_idx + 97 * p + (0 if opt.upper() == "COBYLA" else 17)
                t0 = time.time()
                theta, final_metrics, traj = optimize_qaoa(
                    g=g,
                    p=p,
                    optimizer=opt,
                    bounds=bounds,
                    optimal_cut=optimal_cut,
                    optimal_bitstrings=optimal_bitstrings,
                    seed=run_seed,
                    cobyla_maxiter=cobyla_maxiter,
                    spsa_iterations=spsa_iterations,
                )
                runtime = time.time() - t0
                qc = build_qaoa_circuit(g, theta, p)
                exact = evaluate_exact(g, qc, optimal_cut, optimal_bitstrings)
                sampled = sample_from_exact(g, qc, optimal_cut, optimal_bitstrings, shots=shots, seed=run_seed + 13)

                theta_cols = {f"theta_{i}": float(v) for i, v in enumerate(theta)}
                for step in traj:
                    trajectory_rows.append({
                        "graph_id": gid,
                        "graph_type": gt,
                        "graph_seed": gseed,
                        **feats,
                        "qaoa_depth_p": p,
                        "optimizer": opt,
                        **step,
                    })

                for topo in topologies:
                    hw = transpiled_metrics(qc, topo, n, transpile_level, seed=run_seed)
                    cx_per_edge = hw["transpiled_cx"] / feats["num_edges"] if feats["num_edges"] else 0.0
                    cx_per_layer = hw["transpiled_cx"] / p if p else 0.0
                    cx_per_edge_per_layer = hw["transpiled_cx"] / (feats["num_edges"] * p) if feats["num_edges"] and p else 0.0
                    base = {
                        "graph_id": gid,
                        "graph_type": gt,
                        "graph_seed": gseed,
                        **feats,
                        "optimal_cut": optimal_cut,
                        "qaoa_depth_p": p,
                        "optimizer": opt,
                        "runtime_seconds": runtime,
                        "num_function_evaluations": final_metrics["num_function_evaluations"],
                        **theta_cols,
                        **exact,
                        "empirical_expected_ratio_sampled": sampled["empirical_expected_ratio"],
                        "sampled_best_ratio": sampled["best_ratio"],
                        "shots": shots,
                        **hw,
                        "cx_per_edge": cx_per_edge,
                        "cx_per_layer": cx_per_layer,
                        "cx_per_edge_per_layer": cx_per_edge_per_layer,
                    }
                    qaoa_rows.append(base)
                    topology_rows.append({
                        "graph_id": gid,
                        "graph_type": gt,
                        "graph_seed": gseed,
                        **feats,
                        "qaoa_depth_p": p,
                        "optimizer": opt,
                        **hw,
                        "cx_per_edge": cx_per_edge,
                        "cx_per_layer": cx_per_layer,
                        "cx_per_edge_per_layer": cx_per_edge_per_layer,
                    })

                if cfg.get("noise", {}).get("enabled", False):
                    noise_topologies = cfg["noise"].get("topologies", [primary_topology])
                    noise_shots = int(cfg["noise"].get("shots", shots))
                    for topo in noise_topologies:
                        cmap = coupling_map_for_topology(topo, n)
                        for ns in cfg["noise"].get("settings", []):
                            setting = NoiseSetting(
                                name=str(ns["name"]),
                                depol_1q=float(ns.get("depol_1q", 0.0)),
                                depol_2q=float(ns.get("depol_2q", 0.0)),
                                readout=float(ns.get("readout", 0.0)),
                            )
                            if setting.name == "noiseless" or (setting.depol_1q == 0 and setting.depol_2q == 0 and setting.readout == 0):
                                noisy_eval = {
                                    "empirical_expected_ratio": float(exact["exact_expected_ratio"]),
                                    "expected_cut": float(exact["expected_cut"]),
                                    "optimal_solution_probability": float(exact["optimal_solution_probability"]),
                                    "best_ratio": float(exact["best_ratio"]),
                                    "best_cut": float(exact["best_cut"]),
                                }
                            else:
                                simulator, basis_gates = build_aer_simulator(setting, seed=run_seed)
                                noisy_eval = evaluate_noisy_counts(
                                    g=g,
                                    qc=qc,
                                    simulator=simulator,
                                    coupling_map=cmap,
                                    basis_gates=MEASUREMENT_BASIS_GATES,
                                    optimization_level=transpile_level,
                                    shots=noise_shots,
                                    seed=run_seed + 23,
                                    optimal_cut=optimal_cut,
                                    optimal_bitstrings=optimal_bitstrings,
                                )
                            noise_rows.append({
                                "graph_id": gid,
                                "graph_type": gt,
                                "graph_seed": gseed,
                                **feats,
                                "qaoa_depth_p": p,
                                "optimizer": opt,
                                "topology": topo,
                                "noise_setting": setting.name,
                                "depol_1q": setting.depol_1q,
                                "depol_2q": setting.depol_2q,
                                "readout": setting.readout,
                                "shots": noise_shots,
                                "exact_expected_ratio": float(exact["exact_expected_ratio"]),
                                **noisy_eval,
                                "quality_drop_from_exact": float(exact["exact_expected_ratio"]) - float(noisy_eval["empirical_expected_ratio"]),
                            })

    qaoa_df = pd.DataFrame(qaoa_rows)
    topology_df = pd.DataFrame(topology_rows)
    noise_df = pd.DataFrame(noise_rows)
    traj_df = pd.DataFrame(trajectory_rows)
    baseline_df = pd.DataFrame(baseline_rows)

    paths = {
        "qaoa_results": str(save_csv(qaoa_df, output_dir / "qaoa_results.csv")),
        "topology_metrics": str(save_csv(topology_df, output_dir / "topology_metrics.csv")),
        "noise_results": str(save_csv(noise_df, output_dir / "noise_results.csv")),
        "optimizer_trajectories": str(save_csv(traj_df, output_dir / "optimizer_trajectories.csv")),
        "classical_baselines": str(save_csv(baseline_df, output_dir / "classical_baselines.csv")),
    }

    summaries = make_summaries(qaoa_df, noise_df, baseline_df, primary_topology=primary_topology)
    for name_, df in summaries.items():
        paths[name_] = str(save_csv(df, output_dir / f"{name_}.csv"))

    manifest = {
        "experiment_name": name,
        "runtime_seconds": time.time() - start,
        "python_version": platform.python_version(),
        "num_qaoa_rows": len(qaoa_df),
        "num_noise_rows": len(noise_df),
        "num_graph_instances": len(instances),
        "primary_topology": primary_topology,
        "research_questions": {
            "RQ1": "Depth-cost trade-off",
            "RQ2": "Topology sensitivity",
            "RQ3": "Noise-aware depth robustness",
        },
    }
    paths["results_manifest"] = str(save_json(manifest, output_dir / "results_manifest.json"))

    figure_paths = make_figures(output_dir, figure_dir, primary_topology=primary_topology)
    for pth in figure_paths:
        paths[f"figure_{pth.stem}"] = str(pth)

    return paths
