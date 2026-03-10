"""Experiment comparison helpers with metric direction awareness."""

from __future__ import annotations

from typing import Any


HIGHER_BETTER = {
    "total_return",
    "cagr",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "win_rate",
    "profit_factor",
    "expectancy",
}
LOWER_ABS_BETTER = {"max_drawdown"}


def compare_experiments(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare experiment metrics and return delta table rows."""
    rows: list[dict[str, Any]] = []
    old_m = old.get("metrics", {})
    new_m = new.get("metrics", {})
    keys = sorted(set(old_m.keys()) | set(new_m.keys()))

    for metric in keys:
        old_val = float(old_m.get(metric, 0.0))
        new_val = float(new_m.get(metric, 0.0))
        delta = new_val - old_val
        pct_change = (delta / abs(old_val)) if old_val != 0 else 0.0

        if metric in HIGHER_BETTER:
            improved = new_val > old_val
        elif metric in LOWER_ABS_BETTER:
            improved = abs(new_val) < abs(old_val)
        else:
            improved = False

        rows.append(
            {
                "metric": metric,
                "old_value": old_val,
                "new_value": new_val,
                "delta": delta,
                "pct_change": pct_change,
                "improved": improved,
            }
        )
    return rows
