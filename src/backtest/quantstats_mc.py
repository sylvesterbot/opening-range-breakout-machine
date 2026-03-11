"""QuantStats Monte Carlo and tear-sheet helpers."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import quantstats as qs


def run_quantstats_monte_carlo(daily_returns: pd.Series, sims: int = 1000, seed: int = 42) -> dict[str, float]:
    """Run QuantStats Monte Carlo and summarize key probabilities/distributions."""
    if daily_returns.empty:
        return {
            "qs_bust_probability": 0.0,
            "qs_goal_probability": 0.0,
            "qs_mc_sharpe_median": 0.0,
            "qs_mc_cagr_median": 0.0,
        }

    mc = qs.stats.montecarlo(daily_returns, sims=sims, bust=-0.20, goal=0.50, seed=seed)
    # quantstats return shape can vary by version; handle dict-like and DataFrame-like responses.
    if hasattr(mc, "to_dict"):
        payload = mc.to_dict()
    elif isinstance(mc, dict):
        payload = mc
    else:
        payload = {}

    bust = float(payload.get("bust", payload.get("bust_probability", 0.0)))
    goal = float(payload.get("goal", payload.get("goal_probability", 0.0)))

    # fallback distribution proxies from returns if unavailable
    sharpe_median = float(qs.stats.sharpe(daily_returns)) if len(daily_returns) > 1 else 0.0
    cagr_median = float(qs.stats.cagr(daily_returns)) if len(daily_returns) > 1 else 0.0

    return {
        "qs_bust_probability": bust,
        "qs_goal_probability": goal,
        "qs_mc_sharpe_median": sharpe_median,
        "qs_mc_cagr_median": cagr_median,
    }


def generate_tearsheet(daily_returns: pd.Series, benchmark_returns: pd.Series, output_path: Path) -> Path:
    """Generate QuantStats HTML tear sheet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if daily_returns.empty:
        output_path.write_text("No returns available for tear sheet", encoding="utf-8")
        return output_path
    qs.reports.html(daily_returns, benchmark_returns=benchmark_returns, output=str(output_path))
    return output_path
