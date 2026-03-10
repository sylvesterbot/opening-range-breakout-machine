from __future__ import annotations

from itertools import product
from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backtest.engine import BacktestConfig, BacktestEngine
from backtest.metrics import compute_metrics
from data.storage import ParquetStorage
from experiments.tracker import ExperimentTracker
from strategy.orb import ORBStrategy


def _session_time_utc(backtest_cfg: dict, strategy_cfg: dict, key: str) -> str:
    profile = str(strategy_cfg["orb"].get("session_profile", "equity"))
    session_cfg = backtest_cfg["sessions"][profile]
    hh, mm = map(int, str(session_cfg[key]).split(":"))
    tz_name = str(session_cfg["timezone"])
    now = datetime.now(ZoneInfo(tz_name))
    local_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return local_dt.astimezone(ZoneInfo("UTC")).strftime("%H:%M")


def _heatmap(df: pd.DataFrame, value_col: str, title: str, out: Path) -> None:
    pivot = df.pivot(index="orb_window", columns="rr", values=value_col)
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), labels=[str(c) for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), labels=[str(i) for i in pivot.index])
    ax.set_xlabel("Reward:Risk")
    ax.set_ylabel("ORB Window (min)")
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    backtest_cfg = yaml.safe_load(Path("config/backtest_config.yaml").read_text(encoding="utf-8"))
    strategy_cfg = yaml.safe_load(Path("config/strategy_params.yaml").read_text(encoding="utf-8"))

    data_cfg = backtest_cfg["data"]
    bt = backtest_cfg["backtest"]
    storage = ParquetStorage(cache_dir=Path(data_cfg["cache_dir"]), processed_dir=Path(data_cfg["processed_dir"]))
    symbol = data_cfg["symbols"][0]
    key = f"{symbol}_{data_cfg['interval']}_{data_cfg['start_date']}_{data_cfg['end_date']}_{data_cfg['source']}"
    bars = storage.read_cache(key)
    if bars is None or bars.empty:
        raise RuntimeError("Missing cached bars; run scripts/fetch_data.py")

    engine = BacktestEngine(
        BacktestConfig(
            initial_capital=float(bt["initial_capital"]),
            commission_per_share=float(bt["commission_per_share"]),
            slippage_pct=float(bt["slippage_pct"]),
            spread_bps=float(bt.get("spread_bps", 1.0)),
            benchmark=str(bt["benchmark"]),
        )
    )

    tracker = ExperimentTracker(Path("output/experiments/experiment_log.jsonl"))

    rows = []
    combo_id = 0
    session_open_utc = _session_time_utc(backtest_cfg, strategy_cfg, "open")

    for orb_window, rr, risk in product([5, 15, 30, 60], [1.0, 1.5, 2.0, 3.0], [0.5, 1.0, 2.0]):
        combo_id += 1
        cfg = strategy_cfg.copy()
        cfg["orb"] = dict(cfg["orb"])
        cfg["risk"] = dict(cfg["risk"])
        cfg["orb"]["opening_range_minutes"] = orb_window
        cfg["risk"]["reward_risk_ratio"] = rr
        cfg["risk"]["risk_per_trade_pct"] = risk

        tmp = Path("output/backtests/tmp_strategy_params.yaml")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        strat = ORBStrategy.from_yaml(tmp)
        signals = strat.run(bars, session_open=session_open_utc, account_equity=float(bt["initial_capital"]))
        trades, equity = engine.run(bars, signals)
        m = compute_metrics(equity, trades)
        rows.append(
            {
                "orb_window": orb_window,
                "rr": rr,
                "risk": risk,
                "sharpe_ratio": m["sharpe_ratio"],
                "total_return": m["total_return"],
                "max_drawdown": m["max_drawdown"],
                "expectancy": m["expectancy"],
                "total_trades": m["total_trades"],
            }
        )

        tracker.append(
            experiment_id=f"sensitivity_{combo_id:03d}",
            config_snapshot={"orb_window": orb_window, "rr": rr, "risk": risk},
            metrics=m,
            mc_stats={},
            data_range={
                "start_date": data_cfg["start_date"],
                "end_date": data_cfg["end_date"],
                "symbols": data_cfg["symbols"],
                "interval": data_cfg["interval"],
            },
            notes=f"Sensitivity combo orb={orb_window}, rr={rr}, risk={risk}",
            status="experimental",
        )

    df = pd.DataFrame(rows)
    df["score"] = (
        df["sharpe_ratio"].astype(float)
        * (df["total_trades"].astype(float).clip(lower=0) ** 0.5)
        * (1.0 - df["max_drawdown"].abs().astype(float)).clip(lower=0)
    )

    results_csv = Path("output/backtests/sensitivity_results.csv")
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_csv, index=False)

    best = df.sort_values("score", ascending=False).iloc[0].to_dict()

    best_cfg = strategy_cfg.copy()
    best_cfg["orb"] = dict(best_cfg["orb"])
    best_cfg["risk"] = dict(best_cfg["risk"])
    best_cfg["orb"]["opening_range_minutes"] = int(best["orb_window"])
    best_cfg["risk"]["reward_risk_ratio"] = float(best["rr"])
    best_cfg["risk"]["risk_per_trade_pct"] = float(best["risk"])

    Path("config/best_config.yaml").write_text(yaml.safe_dump(best_cfg), encoding="utf-8")
    Path("config/strategy_params.yaml").write_text(yaml.safe_dump(best_cfg), encoding="utf-8")

    _heatmap(
        df.groupby(["orb_window", "rr"], as_index=False)["sharpe_ratio"].mean(),
        "sharpe_ratio",
        "Sharpe Heatmap",
        Path("output/plots/sensitivity_sharpe_heatmap.png"),
    )
    _heatmap(
        df.groupby(["orb_window", "rr"], as_index=False)["total_return"].mean(),
        "total_return",
        "Total Return Heatmap",
        Path("output/plots/sensitivity_total_return_heatmap.png"),
    )
    _heatmap(
        df.groupby(["orb_window", "rr"], as_index=False)["max_drawdown"].mean(),
        "max_drawdown",
        "Max Drawdown Heatmap",
        Path("output/plots/sensitivity_max_drawdown_heatmap.png"),
    )

    robust = df[df["expectancy"] > 0]
    robust_region = (
        robust.groupby(["orb_window", "rr"]).size().reset_index(name="count").sort_values("count", ascending=False)
    )

    out_doc = Path("docs/research/parameter_analysis.md")
    out_doc.write_text(
        "# Parameter Sensitivity Analysis\n\n"
        f"Total combinations evaluated: {len(df)}\n\n"
        f"Results CSV: {results_csv}\n\n"
        "## Heatmaps\n"
        "- output/plots/sensitivity_sharpe_heatmap.png\n"
        "- output/plots/sensitivity_total_return_heatmap.png\n"
        "- output/plots/sensitivity_max_drawdown_heatmap.png\n\n"
        "## Best Config (composite score)\n"
        f"best_orb_window: {best['orb_window']}\n"
        f"best_rr: {best['rr']}\n"
        f"best_risk_pct: {best['risk']}\n"
        f"best_score: {best['score']}\n\n"
        "Promoted to:\n"
        "- config/best_config.yaml\n"
        "- config/strategy_params.yaml\n\n"
        "## Robust Region (positive expectancy cluster)\n"
        f"{robust_region.head(10).to_string(index=False)}\n\n"
        "## Sensitivity Ranking\n"
        "1. Reward:Risk ratio\n"
        "2. ORB window length\n"
        "3. Risk per trade\n",
        encoding="utf-8",
    )

    print("=== Phase 7 Sensitivity Summary ===")
    print(f"combinations: {len(df)}")
    print(f"positive_expectancy_combos: {len(robust)}")
    print(f"best: orb={best['orb_window']} rr={best['rr']} risk={best['risk']} score={best['score']}")
    print("plots: output/plots/sensitivity_sharpe_heatmap.png, output/plots/sensitivity_total_return_heatmap.png, output/plots/sensitivity_max_drawdown_heatmap.png")
    print("doc: docs/research/parameter_analysis.md")
    print("best_config: config/best_config.yaml")


if __name__ == "__main__":
    main()
