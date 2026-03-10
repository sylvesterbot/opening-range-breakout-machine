"""Monte Carlo visualization utilities."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from backtest.monte_carlo import MonteCarloResult


def generate_monte_carlo_plots(result: MonteCarloResult, output_dir: Path) -> dict[str, Path]:
    """Generate MC histogram, fan chart, drawdown histogram, and convergence plot."""
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    p1 = output_dir / "mc_terminal_equity_hist.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(result.terminal_equities, bins=40, alpha=0.8)
    for q in [5, 25, 50, 75, 95]:
        ax.axvline(np.percentile(result.terminal_equities, q), linestyle="--", label=f"p{q}")
    ax.set_title("Terminal Equity Distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(p1)
    plt.close(fig)
    paths["terminal_hist"] = p1

    p2 = output_dir / "mc_equity_fan_chart.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    for curve in result.equity_curves:
        ax.plot(curve, color="tab:blue", alpha=0.05)
    ax.set_title("Monte Carlo Equity Fan Chart")
    fig.tight_layout()
    fig.savefig(p2)
    plt.close(fig)
    paths["fan_chart"] = p2

    p3 = output_dir / "mc_drawdown_hist.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(result.max_drawdowns, bins=40, alpha=0.8, color="tab:red")
    ax.set_title("Monte Carlo Max Drawdown Distribution")
    fig.tight_layout()
    fig.savefig(p3)
    plt.close(fig)
    paths["drawdown_hist"] = p3

    p4 = output_dir / "mc_convergence.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(result.running_mean)
    ax.set_title("Running Mean of Terminal Equity")
    ax.set_xlabel("Iteration")
    fig.tight_layout()
    fig.savefig(p4)
    plt.close(fig)
    paths["convergence"] = p4

    return paths
