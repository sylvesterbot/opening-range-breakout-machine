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

    bust = float(getattr(mc, "bust_probability", 0.0) or 0.0)
    goal = float(getattr(mc, "goal_probability", 0.0) or 0.0)

    sharpe_median = 0.0
    cagr_median = 0.0

    # Primary path (current quantstats): MonteCarloResult.data is a DataFrame of simulated equity/return paths.
    data = getattr(mc, "data", None)
    if isinstance(data, pd.DataFrame) and not data.empty:
        sharpe_vals: list[float] = []
        cagr_vals: list[float] = []
        for col in data.columns:
            series = pd.to_numeric(data[col], errors="coerce").dropna()
            if len(series) < 2:
                continue
            sim_rets = series.pct_change().dropna()
            if sim_rets.empty:
                continue
            sharpe_vals.append(float(qs.stats.sharpe(sim_rets)))
            cagr_vals.append(float(qs.stats.cagr(sim_rets)))
        if sharpe_vals:
            sharpe_median = float(pd.Series(sharpe_vals).median())
        if cagr_vals:
            cagr_median = float(pd.Series(cagr_vals).median())

    # Backward-compat fallback for dict-like returns and unknown formats.
    if sharpe_median == 0.0 or cagr_median == 0.0:
        payload = mc if isinstance(mc, dict) else {}
        sharpe_median = float(payload.get("sharpe_median", payload.get("median_sharpe", sharpe_median)))
        cagr_median = float(payload.get("cagr_median", payload.get("median_cagr", cagr_median)))

    # Final fallback: deterministic baseline from original daily returns.
    if sharpe_median == 0.0 and len(daily_returns) > 1:
        sharpe_median = float(qs.stats.sharpe(daily_returns))
    if cagr_median == 0.0 and len(daily_returns) > 1:
        cagr_median = float(qs.stats.cagr(daily_returns))

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
