import pandas as pd

from backtest.scientific_validation import (
    bootstrap_metric_ci,
    sensitivity_consistency_score,
    walk_forward_stability_score,
)


def test_bootstrap_metric_ci_basic():
    s = pd.Series([0.1, 0.2, 0.05, 0.3, 0.15])
    out = bootstrap_metric_ci(s, n_bootstrap=200)
    assert "mean" in out and "ci_low" in out and "ci_high" in out
    assert out["ci_low"] <= out["mean"] <= out["ci_high"]


def test_walk_forward_stability_score_basic():
    out = walk_forward_stability_score([0.8, 0.7, 0.9], [0.5, 0.6, 0.4])
    assert out["wf_windows"] == 3.0
    assert out["wf_stability_ratio"] > 0


def test_sensitivity_consistency_score_basic():
    df = pd.DataFrame({"sharpe": [0.5, 0.55, 0.52, 0.48]})
    out = sensitivity_consistency_score(df, metric_col="sharpe")
    assert 0.0 <= out["consistency_score"] <= 1.0
    assert out["metric_std"] >= 0.0
