from __future__ import annotations

from pathlib import Path
import sys
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import benchmark_buy_hold_return, compute_metrics
from data.storage import ParquetStorage
from strategy.orb import ORBStrategy
from visualization.equity_curve import plot_equity_curve


def main() -> None:
    backtest_cfg = yaml.safe_load(Path("config/backtest_config.yaml").read_text(encoding="utf-8"))
    strategy = ORBStrategy.from_yaml(Path("config/strategy_params.yaml"))
    data_cfg = backtest_cfg["data"]
    bt_cfg = backtest_cfg.get("backtest", {
        "initial_capital": 100000,
        "commission_per_share": 0.005,
        "slippage_pct": 0.01,
        "spread_bps": 1.0,
        "benchmark": "SPY",
    })

    storage = ParquetStorage(cache_dir=Path(data_cfg["cache_dir"]), processed_dir=Path(data_cfg["processed_dir"]))
    symbol = data_cfg["symbols"][0]
    key = f"{symbol}_{data_cfg['interval']}_{data_cfg['start_date']}_{data_cfg['end_date']}_{data_cfg['source']}"
    bars = storage.read_cache(key)
    if bars is None or bars.empty:
        raise RuntimeError(f"No cached bars for {key}; run scripts/fetch_data.py first")

    signals = strategy.run(bars, session_open="14:30", account_equity=float(bt_cfg["initial_capital"]))
    engine = BacktestEngine(
        BacktestConfig(
            initial_capital=float(bt_cfg["initial_capital"]),
            commission_per_share=float(bt_cfg["commission_per_share"]),
            slippage_pct=float(bt_cfg["slippage_pct"]),
            spread_bps=float(bt_cfg.get("spread_bps", 1.0)),
            benchmark=str(bt_cfg["benchmark"]),
        )
    )
    trades, equity = engine.run(bars, signals)
    metrics = compute_metrics(equity, trades)
    bench_ret = benchmark_buy_hold_return(bars, float(bt_cfg["initial_capital"]))

    plot_path = plot_equity_curve(equity, Path("output/plots/equity_curve.png"))

    print("=== Phase 5 Backtest Summary ===")
    summary_table = "\n".join([f"{k:>24} | {v}" for k, v in metrics.items()])
    print(summary_table)
    print(f"{'benchmark_buy_hold_return':>24} | {bench_ret}")
    print(f"{'trades':>24} | {len(trades)}")
    print(f"{'equity_plot':>24} | {plot_path}")

    # manual 5-day subset cross-check note
    if not trades.empty:
        pnl_sum = float(trades["net_pnl"].sum())
        total_return_manual = (float(equity.iloc[-1]["equity"]) / float(equity.iloc[0]["equity"])) - 1
        print(f"manual_check_net_pnl_sum: {pnl_sum}")
        print(f"manual_check_total_return: {total_return_manual}")


if __name__ == "__main__":
    main()
