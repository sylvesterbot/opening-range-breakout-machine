from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtest.walk_forward import run_walk_forward


def test_walk_forward_handles_empty() -> None:
    bars = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "symbol"])
    backtest_cfg = {"backtest": {"initial_capital": 100000, "commission_per_share": 0.005, "slippage_pct": 0.01, "spread_bps": 1.0, "benchmark": "SPY"}}
    out = run_walk_forward(bars, backtest_cfg, Path("config/strategy_params.yaml"))
    assert len(out.windows) == 0
    assert out.sharpe_degradation == 0.0
