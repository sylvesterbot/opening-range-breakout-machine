"""ORB strategy orchestration module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging

import pandas as pd
import yaml

from strategy.position_sizing import compute_position_size
from strategy.signals import generate_orb_signals

logger = logging.getLogger(__name__)


@dataclass
class ORBStrategy:
    """Config-driven ORB strategy orchestration."""

    orb_config: dict[str, Any]
    risk_config: dict[str, Any]

    @classmethod
    def from_yaml(cls, config_path: Path) -> "ORBStrategy":
        """Create strategy instance from YAML config."""
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        logger.info("Loaded ORB strategy config from %s", config_path)
        return cls(orb_config=payload["orb"], risk_config=payload["risk"])

    def run(self, bars: pd.DataFrame, session_open: str, account_equity: float = 100_000.0) -> pd.DataFrame:
        """Run ORB signal generation and position sizing.

        Args:
            bars: Input intraday bars.
            session_open: Session open time HH:MM.
            account_equity: Account equity for position sizing.

        Returns:
            DataFrame of trade intents with sizes.
        """
        signals = generate_orb_signals(
            bars=bars,
            opening_range_minutes=int(self.orb_config["opening_range_minutes"]),
            session_open=session_open,
            entry_window_hours=int(self.orb_config["entry_window_hours"]),
            entry_confirmation=str(self.orb_config["entry_confirmation"]),
            volume_threshold_multiplier=float(self.orb_config["volume_threshold_multiplier"]),
            max_entries_per_day=int(self.orb_config["max_entries_per_day"]),
        )

        if signals.empty:
            return signals

        rr = float(self.risk_config["reward_risk_ratio"])
        result = signals.copy()
        sizes: list[float] = []
        stop_prices: list[float] = []
        target_prices: list[float] = []

        for _, row in result.iterrows():
            side = row["side"]
            entry = float(row["entry_price"])
            if side == "long":
                stop = float(row["or_low"])
                risk = entry - stop
                target = entry + rr * risk
            else:
                stop = float(row["or_high"])
                risk = stop - entry
                target = entry - rr * risk

            size = compute_position_size(
                account_equity=account_equity,
                risk_per_trade_pct=float(self.risk_config["risk_per_trade_pct"]),
                entry_price=entry,
                stop_price=stop,
                max_position_pct=float(self.risk_config["max_position_pct"]),
            )
            sizes.append(size)
            stop_prices.append(stop)
            target_prices.append(target)

        result["stop_price"] = stop_prices
        result["target_price"] = target_prices
        result["size"] = sizes
        return result
