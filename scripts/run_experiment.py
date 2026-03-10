from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import compute_metrics
from backtest.monte_carlo import MonteCarloConfig, run_trade_bootstrap_monte_carlo
from data.storage import ParquetStorage
from experiments.comparator import compare_experiments
from experiments.tracker import ExperimentTracker
from strategy.orb import ORBStrategy


def _write_report(path: Path, current: dict, previous: dict | None, comparison: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Experiment Report: {current['experiment_id']}", "", f"Notes: {current['notes']}", ""]
    lines.append("## Metrics")
    for k, v in current["metrics"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    if previous is not None:
        lines.append(f"## Comparison vs {previous['experiment_id']}")
        for row in comparison:
            lines.append(
                f"- {row['metric']}: old={row['old_value']} new={row['new_value']} "
                f"delta={row['delta']} improved={row['improved']}"
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", required=True)
    parser.add_argument("--status", default="experimental")
    args = parser.parse_args()

    root = Path(".")
    backtest_cfg = yaml.safe_load((root / "config/backtest_config.yaml").read_text(encoding="utf-8"))
    strategy_cfg = yaml.safe_load((root / "config/strategy_params.yaml").read_text(encoding="utf-8"))
    mc_cfg = yaml.safe_load((root / "config/monte_carlo_config.yaml").read_text(encoding="utf-8"))["monte_carlo"]

    data_cfg = backtest_cfg["data"]
    bt_cfg = backtest_cfg["backtest"]

    storage = ParquetStorage(cache_dir=Path(data_cfg["cache_dir"]), processed_dir=Path(data_cfg["processed_dir"]))
    symbol = data_cfg["symbols"][0]
    key = f"{symbol}_{data_cfg['interval']}_{data_cfg['start_date']}_{data_cfg['end_date']}_{data_cfg['source']}"
    bars = storage.read_cache(key)
    if bars is None or bars.empty:
        raise RuntimeError(f"No cached bars for {key}; run scripts/fetch_data.py first")

    strategy = ORBStrategy.from_yaml(root / "config/strategy_params.yaml")
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

    mc = run_trade_bootstrap_monte_carlo(
        trades,
        MonteCarloConfig(
            iterations=int(mc_cfg["iterations"]),
            max_iterations=int(mc_cfg["max_iterations"]),
            convergence_threshold=float(mc_cfg["convergence_threshold"]),
            early_stopping=bool(mc_cfg["early_stopping"]),
            slippage_range=tuple(mc_cfg["slippage_range"]),
            random_seed=int(mc_cfg["random_seed"]),
            initial_capital=float(bt_cfg["initial_capital"]),
        ),
    )

    tracker = ExperimentTracker(root / "output/experiments/experiment_log.jsonl")
    record = tracker.append(
        config_snapshot={
            "backtest_config": backtest_cfg,
            "strategy_params": strategy_cfg,
            "monte_carlo": mc_cfg,
        },
        metrics=metrics,
        mc_stats=mc.stats,
        data_range={
            "start_date": data_cfg["start_date"],
            "end_date": data_cfg["end_date"],
            "symbols": data_cfg["symbols"],
            "interval": data_cfg["interval"],
        },
        notes=args.notes,
        status=args.status,
    )

    all_rows = tracker.load_all()
    previous = all_rows[-2] if len(all_rows) > 1 else None
    comparison = compare_experiments(previous, record.__dict__) if previous else []

    report_path = root / f"output/experiment_reports/exp_{record.experiment_id}_report.md"
    _write_report(report_path, record.__dict__, previous, comparison)

    print("=== Experiment Run Complete ===")
    print(f"experiment_id: {record.experiment_id}")
    print(f"status: {record.status}")
    print(f"log_path: {tracker.log_path}")
    print(f"report_path: {report_path}")
    if previous:
        print(f"compared_to: {previous['experiment_id']}")
        print(f"delta_rows: {len(comparison)}")


if __name__ == "__main__":
    main()
