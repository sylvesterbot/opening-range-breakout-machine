from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import compute_metrics
from backtest.monte_carlo import MonteCarloConfig, run_trade_bootstrap_monte_carlo
from backtest.quantstats_mc import generate_tearsheet, run_quantstats_monte_carlo
from data.fetcher import MarketDataFetcher
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


def _load_or_fetch_symbol(symbol: str, cfg: dict, storage: ParquetStorage, fetcher: MarketDataFetcher) -> pd.DataFrame:
    key = f"{symbol}_{cfg['interval']}_{cfg['start_date']}_{cfg['end_date']}_{cfg['source']}"
    bars = storage.read_cache(key)
    if bars is not None and not bars.empty:
        return bars
    bars = fetcher.fetch_symbol(
        symbol=symbol,
        source=cfg["source"],
        fallback_source=cfg.get("fallback_source"),
        interval=cfg["interval"],
        start=cfg["start_date"],
        end=cfg["end_date"],
        asset_class=cfg["asset_class"],
    )
    storage.write_cache(key, bars)
    return bars


def main() -> None:
    load_dotenv()
    root = Path(".")
    backtest_cfg = yaml.safe_load((root / "config/backtest_config.yaml").read_text(encoding="utf-8"))
    strategy_path = root / "config/best_config.yaml"
    if not strategy_path.exists():
        strategy_path = root / "config/strategy_params.yaml"
    strategy = ORBStrategy.from_yaml(strategy_path)

    data_cfg = dict(backtest_cfg["data"])
    data_cfg["symbols"] = ["SPY", "QQQ", "IWM"]
    bt = backtest_cfg["backtest"]
    risk_cfg = strategy.risk_config

    storage = ParquetStorage(cache_dir=Path(data_cfg["cache_dir"]), processed_dir=Path(data_cfg["processed_dir"]))
    fetcher = MarketDataFetcher()

    session_open_utc = _session_time_utc(backtest_cfg, strategy, "open")
    session_close_utc = _session_time_utc(backtest_cfg, strategy, "close")

    per_symbol: dict[str, dict] = {}
    equity_frames: list[pd.DataFrame] = []
    all_trades: list[pd.DataFrame] = []

    for symbol in data_cfg["symbols"]:
        bars = _load_or_fetch_symbol(symbol, data_cfg, storage, fetcher)
        if bars.empty:
            continue
        signals = strategy.run(bars, session_open=session_open_utc, account_equity=float(bt["initial_capital"]))
        engine = BacktestEngine(
            BacktestConfig(
                initial_capital=float(bt["initial_capital"]),
                commission_per_share=float(bt["commission_per_share"]),
                slippage_pct=float(bt["slippage_pct"]),
                spread_bps=float(bt.get("spread_bps", 1.0)),
                benchmark=str(bt["benchmark"]),
                trailing_stop_enabled=bool(risk_cfg.get("trailing_stop_enabled", False)),
                trailing_stop_activation_r=float(risk_cfg.get("trailing_stop_activation_r", 1.0)),
                trailing_stop_trail_r=float(risk_cfg.get("trailing_stop_trail_r", 0.5)),
                exit_before_close_minutes=int(risk_cfg.get("exit_before_close_minutes", 5)),
                session_close_utc=session_close_utc,
            )
        )
        trades, equity = engine.run(bars, signals)
        metrics = compute_metrics(equity, trades)
        per_symbol[symbol] = metrics
        if not equity.empty:
            ef = equity.copy()
            ef = ef.rename(columns={"equity": symbol})
            equity_frames.append(ef[["timestamp", symbol]])
        if not trades.empty:
            t = trades.copy()
            t["symbol"] = symbol
            all_trades.append(t)

    if not equity_frames:
        raise RuntimeError("No symbol equity curves generated for Batch 5")

    merged = equity_frames[0]
    for ef in equity_frames[1:]:
        merged = merged.merge(ef, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").ffill().dropna()

    symbol_cols = [c for c in merged.columns if c != "timestamp"]
    returns = merged[symbol_cols].pct_change().dropna()
    corr = returns.corr()
    portfolio_ret = returns.mean(axis=1)
    portfolio_equity = float(bt["initial_capital"]) * (1 + portfolio_ret).cumprod()
    portfolio_curve = pd.DataFrame({"timestamp": returns.index, "equity": portfolio_equity.values})

    all_trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(columns=["net_pnl"])
    portfolio_metrics = compute_metrics(portfolio_curve, all_trades_df)

    mc_cfg_raw = yaml.safe_load((root / "config/monte_carlo_config.yaml").read_text(encoding="utf-8"))["monte_carlo"]
    mc = run_trade_bootstrap_monte_carlo(
        all_trades_df,
        MonteCarloConfig(
            iterations=int(mc_cfg_raw["iterations"]),
            max_iterations=int(mc_cfg_raw["max_iterations"]),
            convergence_threshold=float(mc_cfg_raw["convergence_threshold"]),
            early_stopping=bool(mc_cfg_raw["early_stopping"]),
            slippage_range=tuple(mc_cfg_raw["slippage_range"]),
            random_seed=int(mc_cfg_raw["random_seed"]),
            initial_capital=float(bt["initial_capital"]),
        ),
    )

    daily_port = portfolio_curve.copy()
    daily_port["date"] = pd.to_datetime(daily_port["timestamp"]).dt.date
    daily_port = daily_port.groupby("date", as_index=False)["equity"].last()
    daily_port["date"] = pd.to_datetime(daily_port["date"])
    daily_returns = daily_port.set_index("date")["equity"].pct_change().dropna()

    spy_bars = _load_or_fetch_symbol("SPY", data_cfg, storage, fetcher)
    spy_bars["date"] = pd.to_datetime(spy_bars["timestamp"], utc=True).dt.date
    spy_daily = spy_bars.groupby("date", as_index=False)["close"].last()
    spy_daily["date"] = pd.to_datetime(spy_daily["date"])
    spy_returns = spy_daily.set_index("date")["close"].pct_change().dropna()

    qs_stats = run_quantstats_monte_carlo(daily_returns, sims=1000, seed=42)
    tearsheet_path = generate_tearsheet(daily_returns, spy_returns, root / "output/reports/tearsheet.html")

    tracker = ExperimentTracker(root / "output/experiments/experiment_log.jsonl")
    record = tracker.append(
        config_snapshot={
            "batch": "batch5",
            "symbols": data_cfg["symbols"],
            "strategy": yaml.safe_load(strategy_path.read_text(encoding="utf-8")),
            "backtest": backtest_cfg,
        },
        metrics=portfolio_metrics,
        mc_stats={**mc.stats, **qs_stats, "equity_corr": corr.to_dict()},
        data_range={
            "start_date": data_cfg["start_date"],
            "end_date": data_cfg["end_date"],
            "symbols": data_cfg["symbols"],
            "interval": data_cfg["interval"],
        },
        notes="Batch 5 multi-symbol portfolio and final report",
        status="improvement",
    )

    all_rows = tracker.load_all()
    primary = [r for r in all_rows if str(r.get("experiment_id", "")).startswith("experiment_")]
    prev = primary[-2] if len(primary) > 1 else None
    delta = compare_experiments(prev, record.__dict__) if prev else []

    report = root / "output/reports/final_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Report (Batch 5)",
        "",
        f"Experiment ID: {record.experiment_id}",
        f"Tearsheet: {tearsheet_path}",
        "",
        "## Per-Symbol Metrics",
    ]
    for symbol, m in per_symbol.items():
        lines.append(f"### {symbol}")
        for k, v in m.items():
            lines.append(f"- {k}: {v}")

    lines += ["", "## Portfolio Metrics (Equal Weight)"]
    for k, v in portfolio_metrics.items():
        lines.append(f"- {k}: {v}")

    lines += ["", "## Equity Correlation"]
    lines.append(corr.to_string())

    lines += ["", "## Monte Carlo (Trade Bootstrap + QuantStats)"]
    for k, v in {**mc.stats, **qs_stats}.items():
        lines.append(f"- {k}: {v}")

    lines += ["", "## Experiment History (primary)"]
    for r in primary:
        lines.append(
            f"- {r['experiment_id']}: total_return={r['metrics'].get('total_return')}, "
            f"sharpe={r['metrics'].get('sharpe_ratio')}, max_dd={r['metrics'].get('max_drawdown')}"
        )

    lines += ["", "## Delta vs Previous Experiment"]
    for row in delta:
        lines.append(
            f"- {row['metric']}: old={row['old_value']} new={row['new_value']} "
            f"delta={row['delta']} improved={row['improved']}"
        )

    lines += [
        "",
        "## Sensitivity + Walk-forward Summary",
        "- Sensitivity heatmaps: output/plots/sensitivity_*.png",
        "- Parameter analysis: docs/research/parameter_analysis.md",
        "- Walk-forward metrics logged in experiment_005 mc_stats",
        "",
        "## Risk Assessment",
        "- Edge remains modest and sensitive to regime changes.",
        "- Walk-forward degradation indicates caution before live deployment.",
        "- Slippage/spread assumptions should be stress-tested further.",
        "",
        "## Live Trading Recommendations",
        "1. Paper trade with strict risk caps for at least 4–8 weeks.",
        "2. Add production safeguards (max daily loss, kill switch).",
        "3. Expand OOS validation horizon before scaling.",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")

    print("=== Batch 5 Final Summary ===")
    print(f"experiment_id: {record.experiment_id}")
    print(f"symbols: {list(per_symbol.keys())}")
    print(f"portfolio_total_return: {portfolio_metrics.get('total_return')}")
    print(f"report: {report}")
    print(f"tearsheet: {tearsheet_path}")


if __name__ == "__main__":
    main()
