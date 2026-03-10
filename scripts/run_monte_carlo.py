from __future__ import annotations

from pathlib import Path
import sys
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.monte_carlo import MonteCarloConfig, run_trade_bootstrap_monte_carlo
from strategy.orb import ORBStrategy
from backtest.engine import BacktestConfig, BacktestEngine
from data.storage import ParquetStorage
from visualization.monte_carlo_plots import generate_monte_carlo_plots


def main() -> None:
    backtest_cfg = yaml.safe_load(Path("config/backtest_config.yaml").read_text(encoding="utf-8"))
    mc_cfg_raw = yaml.safe_load(Path("config/monte_carlo_config.yaml").read_text(encoding="utf-8"))["monte_carlo"]
    strategy = ORBStrategy.from_yaml(Path("config/strategy_params.yaml"))

    data_cfg = backtest_cfg["data"]
    bt = backtest_cfg["backtest"]
    storage = ParquetStorage(cache_dir=Path(data_cfg["cache_dir"]), processed_dir=Path(data_cfg["processed_dir"]))
    symbol = data_cfg["symbols"][0]
    key = f"{symbol}_{data_cfg['interval']}_{data_cfg['start_date']}_{data_cfg['end_date']}_{data_cfg['source']}"
    bars = storage.read_cache(key)
    if bars is None or bars.empty:
        raise RuntimeError(f"No cached bars for {key}; run scripts/fetch_data.py first")

    signals = strategy.run(bars, session_open="14:30", account_equity=float(bt["initial_capital"]))
    engine = BacktestEngine(
        BacktestConfig(
            initial_capital=float(bt["initial_capital"]),
            commission_per_share=float(bt["commission_per_share"]),
            slippage_pct=float(bt["slippage_pct"]),
            spread_bps=float(bt.get("spread_bps", 1.0)),
            benchmark=str(bt["benchmark"]),
        )
    )
    trades, _ = engine.run(bars, signals)

    mc_cfg = MonteCarloConfig(
        iterations=int(mc_cfg_raw["iterations"]),
        max_iterations=int(mc_cfg_raw["max_iterations"]),
        convergence_threshold=float(mc_cfg_raw["convergence_threshold"]),
        early_stopping=bool(mc_cfg_raw["early_stopping"]),
        slippage_range=tuple(mc_cfg_raw["slippage_range"]),
        random_seed=int(mc_cfg_raw["random_seed"]),
        initial_capital=float(bt["initial_capital"]),
    )

    result = run_trade_bootstrap_monte_carlo(trades, mc_cfg)
    plots = generate_monte_carlo_plots(result, Path("output/plots"))

    print("=== Phase 6 Monte Carlo Summary ===")
    print(f"iterations_completed: {result.iterations_completed}")
    for k, v in result.stats.items():
        print(f"{k}: {v}")
    for k, v in plots.items():
        print(f"plot_{k}: {v}")


if __name__ == "__main__":
    main()
