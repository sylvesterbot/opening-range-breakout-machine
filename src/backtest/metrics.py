"""Performance metrics for backtest outputs."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_metrics(equity_curve: pd.DataFrame, trades: pd.DataFrame) -> dict[str, float]:
    """Compute the 12 required performance metrics from equity and trades."""
    if equity_curve.empty:
        return {k: 0.0 for k in [
            "total_return","cagr","sharpe_ratio","sortino_ratio","calmar_ratio","max_drawdown",
            "win_rate","profit_factor","avg_win_avg_loss","expectancy","total_trades","avg_trade_duration_bars",
        ]}

    equity = equity_curve["equity"].astype(float)
    initial = float(equity.iloc[0])
    final = float(equity.iloc[-1])
    total_return = (final / initial) - 1 if initial else 0.0

    rets = equity.pct_change().dropna()
    periods_per_year = 252 * 78  # 5-min bars in regular session
    years = max(len(equity) / periods_per_year, 1 / 252)
    cagr = (final / initial) ** (1 / years) - 1 if initial > 0 and final > 0 else 0.0

    std = float(rets.std()) if len(rets) else 0.0
    sharpe = float((rets.mean() / std) * math.sqrt(periods_per_year)) if std > 0 else 0.0
    downside = rets[rets < 0]
    down_std = float(downside.std()) if len(downside) else 0.0
    sortino = float((rets.mean() / down_std) * math.sqrt(periods_per_year)) if down_std > 0 else 0.0

    roll_max = equity.cummax()
    dd = (equity / roll_max) - 1
    max_dd = float(dd.min()) if len(dd) else 0.0
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0

    wins = trades[trades["net_pnl"] > 0] if not trades.empty else pd.DataFrame()
    losses = trades[trades["net_pnl"] < 0] if not trades.empty else pd.DataFrame()
    total_trades = int(len(trades))
    win_rate = float(len(wins) / total_trades) if total_trades else 0.0
    gross_profit = float(wins["net_pnl"].sum()) if not wins.empty else 0.0
    gross_loss = float(abs(losses["net_pnl"].sum())) if not losses.empty else 0.0
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 0.0
    avg_win = float(wins["net_pnl"].mean()) if not wins.empty else 0.0
    avg_loss = float(abs(losses["net_pnl"].mean())) if not losses.empty else 0.0
    avg_win_avg_loss = float(avg_win / avg_loss) if avg_loss > 0 else 0.0
    expectancy = float(win_rate * avg_win - (1 - win_rate) * avg_loss)
    avg_duration = float(trades["hold_bars"].mean()) if total_trades else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win_avg_loss": avg_win_avg_loss,
        "expectancy": expectancy,
        "total_trades": float(total_trades),
        "avg_trade_duration_bars": avg_duration,
    }


def benchmark_buy_hold_return(bars: pd.DataFrame, initial_capital: float) -> float:
    """Compute simple buy-and-hold return over bar span."""
    if bars.empty:
        return 0.0
    start = float(bars.iloc[0]["open"])
    end = float(bars.iloc[-1]["close"])
    if start <= 0:
        return 0.0
    return (end / start) - 1
