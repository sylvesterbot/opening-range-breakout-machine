"""Scientific validation helpers for Phase 10 Batch 3."""

from __future__ import annotations

import numpy as np
import pandas as pd


def bootstrap_metric_ci(values: pd.Series, n_bootstrap: int = 1000, ci: float = 0.95, seed: int = 42) -> dict[str, float]:
    """Return bootstrap CI over a metric sample."""
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}

    rng = np.random.default_rng(seed)
    arr = s.to_numpy(dtype=float)
    means = []
    for _ in range(max(n_bootstrap, 100)):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means.append(float(np.mean(sample)))

    alpha = (1.0 - ci) / 2.0
    lo = float(np.quantile(means, alpha))
    hi = float(np.quantile(means, 1.0 - alpha))
    return {"mean": float(np.mean(arr)), "ci_low": lo, "ci_high": hi}


def walk_forward_stability_score(in_sample_sharpes: list[float], out_sample_sharpes: list[float]) -> dict[str, float]:
    """Compute walk-forward stability as out/in ratio and degradation."""
    ins = pd.Series(in_sample_sharpes, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    outs = pd.Series(out_sample_sharpes, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if ins.empty or outs.empty:
        return {"wf_stability_ratio": 0.0, "wf_degradation": 0.0, "wf_windows": 0.0}

    m_in = float(ins.mean())
    m_out = float(outs.mean())
    ratio = float(m_out / m_in) if abs(m_in) > 1e-9 else 0.0
    degr = float((m_in - m_out) / max(abs(m_in), 1e-9))
    return {"wf_stability_ratio": ratio, "wf_degradation": degr, "wf_windows": float(min(len(ins), len(outs)))}


def sensitivity_consistency_score(results: pd.DataFrame, metric_col: str = "sharpe") -> dict[str, float]:
    """Estimate consistency from parameter sensitivity grid outputs."""
    if results is None or results.empty or metric_col not in results.columns:
        return {"consistency_score": 0.0, "metric_std": 0.0}

    vals = pd.to_numeric(results[metric_col], errors="coerce").dropna()
    if vals.empty:
        return {"consistency_score": 0.0, "metric_std": 0.0}

    std = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
    denom = abs(float(vals.mean())) + 1e-9
    cv = std / denom
    score = float(max(0.0, 1.0 - min(cv, 1.0)))
    return {"consistency_score": score, "metric_std": std}
