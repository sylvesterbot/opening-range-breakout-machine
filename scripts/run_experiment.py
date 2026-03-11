from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import compute_metrics
from backtest.monte_carlo import MonteCarloConfig, run_trade_bootstrap_monte_carlo
from backtest.quantstats_mc import generate_tearsheet, run_quantstats_monte_carlo
from backtest.walk_forward import run_walk_forward
from data.storage import ParquetStorage
from experiments.comparator import compare_experiments
from experiments.tracker import ExperimentTracker
from strategy.orb import ORBStrategy


def _session_time_utc(backtest_cfg: dict, strategy: ORBStrategy, key: str) -> str:
    profile = str(strategy.orb_config.get("session_profile", "equity"))
    session_cfg = backtest_cfg["sessions"][profile]
    hh, mm = map(int, str(session_cfg[key]).split(":"))
    tz_name = str(session_cfg["timezone"])
    now = datetime.now(ZoneInfo(tz_name))
    local_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return local_dt.astimezone(ZoneInfo("UTC")).strftime("%H:%M")


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
    risk_cfg = strategy.risk_config
    session_open_utc = _session_time_utc(backtest_cfg, strategy, "open")
    session_close_utc = _session_time_utc(backtest_cfg, strategy, "close")
    signals = strategy.run(bars, session_open=session_open_utc, account_equity=float(bt_cfg["initial_capital"]))

    engine = BacktestEngine(
        BacktestConfig(
            initial_capital=float(bt_cfg["initial_capital"]),
            commission_per_share=float(bt_cfg["commission_per_share"]),
            slippage_pct=float(bt_cfg["slippage_pct"]),
            spread_bps=float(bt_cfg.get("spread_bps", 1.0)),
            benchmark=str(bt_cfg["benchmark"]),
            trailing_stop_enabled=bool(risk_cfg.get("trailing_stop_enabled", False)),
            trailing_stop_activation_r=float(risk_cfg.get("trailing_stop_activation_r", 1.0)),
            trailing_stop_trail_r=float(risk_cfg.get("trailing_stop_trail_r", 0.5)),
            exit_before_close_minutes=int(risk_cfg.get("exit_before_close_minutes", 5)),
            session_close_utc=session_close_utc,
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

    daily_equity = equity.copy()
    daily_equity["date"] = daily_equity["timestamp"].dt.date
    daily_eq = daily_equity.groupby("date", as_index=False)["equity"].last()
    daily_eq["date"] = pd.to_datetime(daily_eq["date"])
    daily_returns = daily_eq.set_index("date")["equity"].pct_change().dropna()

    benchmark_returns = bars.copy().sort_values("timestamp")
    benchmark_returns["date"] = pd.to_datetime(benchmark_returns["timestamp"], utc=True).dt.date
    bench_daily = benchmark_returns.groupby("date", as_index=False)["close"].last()
    bench_daily["date"] = pd.to_datetime(bench_daily["date"])
    bench_returns = bench_daily.set_index("date")["close"].pct_change().dropna()

    qs_stats = run_quantstats_monte_carlo(daily_returns, sims=1000, seed=42)
    tearsheet_path = generate_tearsheet(
        daily_returns,
        bench_returns,
        root / "output/reports/tearsheet.html",
    )

    wf = run_walk_forward(
        bars,
        backtest_cfg,
        root / "config/strategy_params.yaml",
        train_months=6,
        test_months=1,
        session_open_utc=session_open_utc,
    )

    mc_stats = dict(mc.stats)
    mc_stats.update(qs_stats)
    mc_stats.update(
        {
            "wf_in_sample_sharpe_mean": wf.in_sample_sharpe_mean,
            "wf_out_sample_sharpe_mean": wf.out_sample_sharpe_mean,
            "wf_sharpe_degradation": wf.sharpe_degradation,
            "wf_windows": float(len(wf.windows)),
        }
    )

    tracker = ExperimentTracker(root / "output/experiments/experiment_log.jsonl")
    record = tracker.append(
        config_snapshot={
            "backtest_config": backtest_cfg,
            "strategy_params": strategy_cfg,
            "monte_carlo": mc_cfg,
        },
        metrics=metrics,
        mc_stats=mc_stats,
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
    primary_rows = [r for r in all_rows if str(r.get("experiment_id", "")).startswith("experiment_")]
    previous = primary_rows[-2] if len(primary_rows) > 1 else None
    comparison = compare_experiments(previous, record.__dict__) if previous else []

    report_path = root / f"output/experiment_reports/exp_{record.experiment_id}_report.md"
    _write_report(report_path, record.__dict__, previous, comparison)

    print("=== Experiment Run Complete ===")
    print(f"experiment_id: {record.experiment_id}")
    print(f"status: {record.status}")
    print(f"log_path: {tracker.log_path}")
    print(f"report_path: {report_path}")
    print(f"tearsheet_path: {tearsheet_path}")
    print(f"walk_forward_windows: {len(wf.windows)}")
    print(f"walk_forward_sharpe_degradation: {wf.sharpe_degradation}")
    if previous:
        print(f"compared_to: {previous['experiment_id']}")
        print(f"delta_rows: {len(comparison)}")


if __name__ == "__main__":
    main()
