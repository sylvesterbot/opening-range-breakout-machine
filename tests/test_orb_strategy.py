from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from strategy.position_sizing import compute_position_size
from strategy.signals import generate_orb_signals
from strategy.orb import ORBStrategy


def _sample_intraday() -> pd.DataFrame:
    idx = pd.date_range("2026-03-03 14:30", periods=8, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "symbol": ["SPY"] * 8,
            "open": [100.0, 100.5, 100.2, 100.4, 101.2, 101.4, 101.0, 100.8],
            "high": [100.6, 100.7, 100.5, 101.0, 101.5, 101.6, 101.1, 100.9],
            "low": [99.8, 100.1, 100.0, 100.2, 100.9, 100.8, 100.6, 100.5],
            "close": [100.5, 100.2, 100.4, 100.95, 101.4, 101.0, 100.8, 100.6],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 900, 800],
            "source": ["test"] * 8,
            "asset_class": ["equity"] * 8,
        }
    )


def test_compute_position_size_guards_and_cap() -> None:
    size = compute_position_size(account_equity=100_000, risk_per_trade_pct=1.0, entry_price=100, stop_price=99, max_position_pct=10.0)
    assert size == 100.0

    bad = compute_position_size(account_equity=100_000, risk_per_trade_pct=1.0, entry_price=100, stop_price=100, max_position_pct=10.0)
    assert bad == 0.0


def test_generate_orb_signals_long_breakout() -> None:
    bars = _sample_intraday()
    out = generate_orb_signals(
        bars,
        opening_range_minutes=15,
        session_open="14:30",
        entry_window_hours=2,
        entry_confirmation="close",
        volume_threshold_multiplier=1.5,
        max_entries_per_day=1,
    )
    assert len(out) == 1
    assert out.iloc[0]["side"] == "long"


def test_orb_strategy_uses_yaml_config(tmp_path: Path) -> None:
    cfg = {
        "orb": {
            "opening_range_minutes": 15,
            "entry_confirmation": "close",
            "volume_threshold_multiplier": 1.5,
            "entry_window_hours": 2,
            "max_entries_per_day": 1,
        },
        "risk": {
            "risk_per_trade_pct": 1.0,
            "max_position_pct": 10.0,
            "reward_risk_ratio": 1.5,
            "trailing_stop_enabled": False,
            "trailing_stop_activation_r": 1.0,
            "trailing_stop_trail_r": 0.5,
            "exit_before_close_minutes": 5,
        },
    }
    p = tmp_path / "strategy_params.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    strat = ORBStrategy.from_yaml(p)
    trades = strat.run(_sample_intraday(), session_open="14:30")
    assert len(trades) == 1
    assert "size" in trades.columns
