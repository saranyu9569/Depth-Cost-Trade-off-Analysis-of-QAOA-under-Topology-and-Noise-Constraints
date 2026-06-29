from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_figures(output_dir: str | Path, figure_dir: str | Path, primary_topology: str = "linear") -> list[Path]:
    output_dir = Path(output_dir)
    figure_dir = Path(figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    qaoa = pd.read_csv(output_dir / "qaoa_results.csv")
    noise_path = output_dir / "noise_results.csv"
    noise = pd.read_csv(noise_path) if noise_path.exists() else pd.DataFrame()
    marginal_path = output_dir / "summary_marginal_depth_cost.csv"
    marginal = pd.read_csv(marginal_path) if marginal_path.exists() else pd.DataFrame()

    primary = qaoa[qaoa["topology"] == primary_topology].copy()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for opt, sub in primary.groupby("optimizer"):
        stats = sub.groupby("qaoa_depth_p")["exact_expected_ratio"].agg(["mean", "std"]).reset_index()
        ax.errorbar(stats["qaoa_depth_p"], stats["mean"], yerr=stats["std"], marker="o", capsize=3, label=opt)
    ax.set_title("Expected QAOA solution quality vs depth")
    ax.set_xlabel("QAOA depth p")
    ax.set_ylabel("Exact expected approximation ratio")
    ax.set_ylim(0.55, 1.0)
    ax.legend()
    paths.append(figure_dir / "exact_ratio_vs_depth.png")
    _save(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    stats = qaoa.groupby(["topology", "qaoa_depth_p"])["transpiled_cx"].mean().reset_index()
    for topo, sub in stats.groupby("topology"):
        ax.plot(sub["qaoa_depth_p"], sub["transpiled_cx"], marker="o", label=topo)
    ax.set_title("Topology-induced CX cost vs QAOA depth")
    ax.set_xlabel("QAOA depth p")
    ax.set_ylabel("Mean transpiled CX count")
    ax.legend(fontsize=8)
    paths.append(figure_dir / "cx_count_vs_depth_by_topology.png")
    _save(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    stats = qaoa.groupby(["topology", "qaoa_depth_p"])["cx_per_edge_per_layer"].mean().reset_index()
    for topo, sub in stats.groupby("topology"):
        ax.plot(sub["qaoa_depth_p"], sub["cx_per_edge_per_layer"], marker="o", label=topo)
    ax.set_title("Normalized CX cost by topology")
    ax.set_xlabel("QAOA depth p")
    ax.set_ylabel("CX per graph edge per QAOA layer")
    ax.legend(fontsize=8)
    paths.append(figure_dir / "normalized_cx_cost_by_topology.png")
    _save(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for topo, sub in qaoa.groupby("topology"):
        ax.scatter(sub["transpiled_cx"], sub["exact_expected_ratio"], s=16, alpha=0.55, label=topo)
    ax.set_title("Quality-cost trade-off by topology")
    ax.set_xlabel("Transpiled CX count")
    ax.set_ylabel("Exact expected approximation ratio")
    ax.legend(fontsize=8)
    paths.append(figure_dir / "quality_vs_cx_by_topology.png")
    _save(fig, paths[-1])

    if not marginal.empty:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        labels = [f"{r.transition}\n{r.optimizer}" for _, r in marginal.iterrows()]
        ax.bar(labels, marginal["mean_quality_gain_per_cx"])
        ax.set_title("Marginal quality gain per additional CX")
        ax.set_ylabel("Mean quality gain / CX increase")
        ax.tick_params(axis="x", rotation=35)
        paths.append(figure_dir / "marginal_quality_gain_per_cx.png")
        _save(fig, paths[-1])

    if not noise.empty:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for setting, sub in noise.groupby("noise_setting"):
            stats = sub.groupby("qaoa_depth_p")["empirical_expected_ratio"].mean().reset_index()
            ax.plot(stats["qaoa_depth_p"], stats["empirical_expected_ratio"], marker="o", label=setting)
        ax.set_title("Noisy QAOA quality vs depth")
        ax.set_xlabel("QAOA depth p")
        ax.set_ylabel("Empirical expected approximation ratio")
        ax.set_ylim(0.45, 1.0)
        ax.legend(fontsize=8)
        paths.append(figure_dir / "noisy_ratio_vs_depth.png")
        _save(fig, paths[-1])

        fig, ax = plt.subplots(figsize=(7, 4.5))
        noisy_only = noise[noise["noise_setting"] != "noiseless"]
        for setting, sub in noisy_only.groupby("noise_setting"):
            stats = sub.groupby("qaoa_depth_p")["quality_drop_from_exact"].mean().reset_index()
            ax.plot(stats["qaoa_depth_p"], stats["quality_drop_from_exact"], marker="o", label=setting)
        ax.set_title("Quality drop under noise")
        ax.set_xlabel("QAOA depth p")
        ax.set_ylabel("Exact ratio - noisy empirical ratio")
        ax.legend(fontsize=8)
        paths.append(figure_dir / "quality_drop_under_noise.png")
        _save(fig, paths[-1])

    return paths
