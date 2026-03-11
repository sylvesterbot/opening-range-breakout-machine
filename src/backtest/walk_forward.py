"""Walk-forward validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path

import pandas as pd
import yaml

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import compute_metrics
from strategy.orb import ORBStrategy


@dataclass
class WalkForwardResult:
    """Walk-forward result container."""

    windows: list[dict]
    in_sample_sharpe_mean: float
    out_sample_sharpe_mean: float
    sharpe_degradation: float


def run_walk_forward(
    bars: pd.DataFrame,
    backtest_cfg: dict,
    strategy_path: Path,
    train_months: int = 6,
    test_months: int = 1,
    session_open_utc: str = "14:30",
) -> WalkForwardResult:
    """Run rolling train/test walk-forward over intraday bars."""
    if bars.empty:
        return WalkForwardResult([], 0.0, 0.0, 0.0)

    bars = bars.copy()
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
    bars = bars.sort_values("timestamp")

    start = bars["timestamp"].min().normalize()
    end = bars["timestamp"].max().normalize()

    bt = backtest_cfg["backtest"]
    engine_cfg = BacktestConfig(
        initial_capital=float(bt["initial_capital"]),
        commission_per_share=float(bt["commission_per_share"]),
        slippage_pct=float(bt["slippage_pct"]),
        spread_bps=float(bt.get("spread_bps", 1.0)),
        benchmark=str(bt["benchmark"]),
    )

    windows: list[dict] = []
    cursor = start
    while cursor < end:
        train_end = cursor + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        if test_end > end:
            break

        train = bars[(bars["timestamp"] >= cursor) & (bars["timestamp"] < train_end)]
        test = bars[(bars["timestamp"] >= train_end) & (bars["timestamp"] < test_end)]
        if train.empty or test.empty:
            cursor = cursor + pd.DateOffset(months=test_months)
            continue

        base = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
        best_cfg = None
        best_sharpe = -1e9

        for orb_window, rr, risk in product([5, 15, 30], [1.0, 1.5, 2.0], [0.5, 1.0]):
            cfg = base.copy()
            cfg["orb"] = dict(cfg["orb"])
            cfg["risk"] = dict(cfg["risk"])
            cfg["orb"]["opening_range_minutes"] = orb_window
            cfg["risk"]["reward_risk_ratio"] = rr
            cfg["risk"]["risk_per_trade_pct"] = risk

            tmp = Path("output/backtests/wf_tmp_strategy.yaml")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
            strat = ORBStrategy.from_yaml(tmp)
            sig_train = strat.run(train, session_open=session_open_utc, account_equity=engine_cfg.initial_capital)
            tr_train, eq_train = BacktestEngine(engine_cfg).run(train, sig_train)
            m_train = compute_metrics(eq_train, tr_train)
            if m_train["sharpe_ratio"] > best_sharpe:
                best_sharpe = m_train["sharpe_ratio"]
                best_cfg = cfg

        tmp_best = Path("output/backtests/wf_best_strategy.yaml")
        tmp_best.write_text(yaml.safe_dump(best_cfg), encoding="utf-8")
        strat_best = ORBStrategy.from_yaml(tmp_best)

        sig_train_best = strat_best.run(train, session_open=session_open_utc, account_equity=engine_cfg.initial_capital)
        tr_train_best, eq_train_best = BacktestEngine(engine_cfg).run(train, sig_train_best)
        m_train_best = compute_metrics(eq_train_best, tr_train_best)

        sig_test = strat_best.run(test, session_open=session_open_utc, account_equity=engine_cfg.initial_capital)
        tr_test, eq_test = BacktestEngine(engine_cfg).run(test, sig_test)
        m_test = compute_metrics(eq_test, tr_test)

        windows.append(
            {
                "train_start": str(cursor.date()),
                "train_end": str((train_end - pd.Timedelta(days=1)).date()),
                "test_end": str((test_end - pd.Timedelta(days=1)).date()),
                "train_sharpe": m_train_best["sharpe_ratio"],
                "test_sharpe": m_test["sharpe_ratio"],
            }
        )

        cursor = cursor + pd.DateOffset(months=test_months)

    if not windows:
        return WalkForwardResult([], 0.0, 0.0, 0.0)

    train_mean = float(pd.DataFrame(windows)["train_sharpe"].mean())
    test_mean = float(pd.DataFrame(windows)["test_sharpe"].mean())
    degradation = abs((train_mean - test_mean) / train_mean) if train_mean != 0 else 0.0
    return WalkForwardResult(windows, train_mean, test_mean, degradation)
