from __future__ import annotations

import pandas as pd

from backtest.monte_carlo import MonteCarloConfig, run_trade_bootstrap_monte_carlo


def test_monte_carlo_runs_and_outputs_stats() -> None:
    trades = pd.DataFrame({"net_pnl": [100.0, -50.0, 80.0, -20.0]})
    cfg = MonteCarloConfig(
        iterations=1200,
        max_iterations=1200,
        convergence_threshold=0.0001,
        early_stopping=False,
        slippage_range=(0.0, 0.0),
        random_seed=7,
        initial_capital=100000.0,
    )
    result = run_trade_bootstrap_monte_carlo(trades, cfg)

    assert result.iterations_completed >= 1000
    assert "p50_terminal_equity" in result.stats
    assert len(result.terminal_equities) == result.iterations_completed
    assert len(result.running_mean) == result.iterations_completed


def test_monte_carlo_handles_empty_trades() -> None:
    trades = pd.DataFrame({"net_pnl": []})
    cfg = MonteCarloConfig(
        iterations=1000,
        max_iterations=1000,
        convergence_threshold=0.001,
        early_stopping=True,
        slippage_range=(0.0, 0.01),
        random_seed=1,
        initial_capital=100000.0,
    )
    result = run_trade_bootstrap_monte_carlo(trades, cfg)
    assert result.iterations_completed == 0
    assert result.stats["probability_of_profit"] == 0.0
