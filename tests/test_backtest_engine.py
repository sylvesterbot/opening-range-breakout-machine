from __future__ import annotations

import pandas as pd

from backtest.engine import BacktestEngine, BacktestConfig
from backtest.metrics import compute_metrics


def _bars() -> pd.DataFrame:
    idx = pd.date_range("2026-03-03 14:30", periods=6, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "symbol": ["SPY"] * 6,
            "open": [100.0, 101.0, 102.0, 101.5, 101.2, 101.0],
            "high": [101.0, 102.0, 103.0, 102.0, 101.5, 101.2],
            "low": [99.5, 100.5, 101.5, 101.0, 100.8, 100.7],
            "close": [100.5, 101.5, 102.5, 101.2, 101.0, 100.8],
        }
    )


def _signals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2026-03-03 14:30", tz="UTC")],
            "symbol": ["SPY"],
            "side": ["long"],
            "entry_price": [100.5],
            "stop_price": [99.5],
            "target_price": [103.0],
            "size": [10.0],
        }
    )


def test_engine_next_bar_open_fill_and_costs() -> None:
    engine = BacktestEngine(
        BacktestConfig(initial_capital=100000, commission_per_share=0.005, slippage_pct=0.01, benchmark="SPY")
    )
    trades, equity = engine.run(_bars(), _signals())

    assert len(trades) == 1
    # next bar open is 101, with +0.01% slippage for long => 101.01
    assert round(float(trades.loc[0, "entry_fill_price"]), 2) == 101.01
    assert float(trades.loc[0, "commission_paid"]) > 0
    assert len(equity) == len(_bars())


def test_metrics_returns_required_keys() -> None:
    engine = BacktestEngine(
        BacktestConfig(initial_capital=100000, commission_per_share=0.005, slippage_pct=0.0, benchmark="SPY")
    )
    trades, equity = engine.run(_bars(), _signals())
    metrics = compute_metrics(equity, trades)

    required = {
        "total_return",
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown",
        "win_rate",
        "profit_factor",
        "avg_win_avg_loss",
        "expectancy",
        "total_trades",
        "avg_trade_duration_bars",
    }
    assert required.issubset(metrics.keys())
