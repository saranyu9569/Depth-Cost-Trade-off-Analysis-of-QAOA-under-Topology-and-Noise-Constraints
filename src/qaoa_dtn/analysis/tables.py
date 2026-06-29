from __future__ import annotations

import pandas as pd


def make_summaries(qaoa_df: pd.DataFrame, noise_df: pd.DataFrame, baseline_df: pd.DataFrame, primary_topology: str) -> dict[str, pd.DataFrame]:
    summaries: dict[str, pd.DataFrame] = {}

    primary = qaoa_df[qaoa_df["topology"] == primary_topology].copy()

    summaries["summary_by_depth"] = (
        primary.groupby("qaoa_depth_p")
        .agg(
            mean_exact_expected_ratio=("exact_expected_ratio", "mean"),
            std_exact_expected_ratio=("exact_expected_ratio", "std"),
            mean_optimal_solution_probability=("optimal_solution_probability", "mean"),
            mean_cx=("transpiled_cx", "mean"),
            mean_depth=("transpiled_depth", "mean"),
            mean_cx_per_edge_per_layer=("cx_per_edge_per_layer", "mean"),
        )
        .reset_index()
    )

    summaries["summary_by_depth_optimizer"] = (
        primary.groupby(["qaoa_depth_p", "optimizer"])
        .agg(
            mean_exact_expected_ratio=("exact_expected_ratio", "mean"),
            std_exact_expected_ratio=("exact_expected_ratio", "std"),
            mean_optimal_solution_probability=("optimal_solution_probability", "mean"),
            mean_cx=("transpiled_cx", "mean"),
            mean_depth=("transpiled_depth", "mean"),
            mean_num_function_evaluations=("num_function_evaluations", "mean"),
        )
        .reset_index()
    )

    summaries["summary_by_topology_depth"] = (
        qaoa_df.groupby(["topology", "qaoa_depth_p"])
        .agg(
            mean_cx=("transpiled_cx", "mean"),
            std_cx=("transpiled_cx", "std"),
            mean_depth=("transpiled_depth", "mean"),
            mean_cx_per_edge_per_layer=("cx_per_edge_per_layer", "mean"),
            mean_exact_expected_ratio=("exact_expected_ratio", "mean"),
        )
        .reset_index()
    )

    # Marginal quality gain and CX cost from p to p+1 by graph and optimizer.
    marg_rows = []
    key_cols = ["graph_id", "optimizer"]
    for key, sub in primary.groupby(key_cols):
        sub = sub.sort_values("qaoa_depth_p")
        rows = {int(r["qaoa_depth_p"]): r for _, r in sub.iterrows()}
        for p0, p1 in [(1, 2), (2, 3)]:
            if p0 in rows and p1 in rows:
                r0, r1 = rows[p0], rows[p1]
                dq = float(r1["exact_expected_ratio"] - r0["exact_expected_ratio"])
                dcx = float(r1["transpiled_cx"] - r0["transpiled_cx"])
                marg_rows.append({
                    "graph_id": key[0],
                    "optimizer": key[1],
                    "transition": f"p{p0}_to_p{p1}",
                    "quality_gain": dq,
                    "cx_increase": dcx,
                    "quality_gain_per_cx": dq / dcx if dcx != 0 else 0.0,
                })
    marginal = pd.DataFrame(marg_rows)
    summaries["summary_marginal_depth_cost"] = (
        marginal.groupby(["transition", "optimizer"])
        .agg(
            mean_quality_gain=("quality_gain", "mean"),
            mean_cx_increase=("cx_increase", "mean"),
            mean_quality_gain_per_cx=("quality_gain_per_cx", "mean"),
            std_quality_gain_per_cx=("quality_gain_per_cx", "std"),
        )
        .reset_index()
        if not marginal.empty else marginal
    )

    if not noise_df.empty:
        summaries["summary_by_noise_depth_optimizer"] = (
            noise_df.groupby(["noise_setting", "topology", "qaoa_depth_p", "optimizer"])
            .agg(
                mean_noisy_expected_ratio=("empirical_expected_ratio", "mean"),
                std_noisy_expected_ratio=("empirical_expected_ratio", "std"),
                mean_quality_drop=("quality_drop_from_exact", "mean"),
                mean_noisy_optimal_probability=("optimal_solution_probability", "mean"),
            )
            .reset_index()
        )
    else:
        summaries["summary_by_noise_depth_optimizer"] = pd.DataFrame()

    summaries["classical_baselines_summary"] = (
        baseline_df.groupby(["graph_type", "num_nodes"])
        .agg(
            mean_random_ratio=("random_mean_ratio", "mean"),
            mean_best_random_ratio=("random_best_ratio", "mean"),
            mean_greedy_ratio=("greedy_ratio", "mean"),
        )
        .reset_index()
        if not baseline_df.empty else baseline_df
    )

    return summaries
