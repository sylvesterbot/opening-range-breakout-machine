"""Backtest engine for ORB strategy outputs."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Runtime configuration for backtesting costs and capital."""

    initial_capital: float
    commission_per_share: float
    slippage_pct: float
    spread_bps: float
    benchmark: str
    trailing_stop_enabled: bool = False
    trailing_stop_activation_r: float = 1.0
    trailing_stop_trail_r: float = 0.5
    exit_before_close_minutes: int = 5
    session_close_utc: str = "21:00"


class BacktestEngine:
    """Simple event-style backtest using next-bar-open fill assumption."""

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def run(self, bars: pd.DataFrame, signals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Execute trades from signal intents against intraday bars.

        Args:
            bars: Market bars with timestamp/open/high/low/close.
            signals: Strategy signals with side/timestamp/size/stop/target.

        Returns:
            tuple of (trades dataframe, equity curve dataframe)
        """
        if bars.empty:
            return pd.DataFrame(), pd.DataFrame()

        bars = bars.sort_values("timestamp").reset_index(drop=True).copy()
        if signals.empty or "timestamp" not in signals.columns:
            eq = pd.DataFrame({"timestamp": pd.to_datetime(bars["timestamp"], utc=True), "equity": self.config.initial_capital})
            return pd.DataFrame(), eq
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
        equity = self.config.initial_capital
        realized = 0.0
        trades: list[dict[str, float | str | pd.Timestamp | int]] = []

        for _, signal in signals.sort_values("timestamp").iterrows():
            s_ts = pd.to_datetime(signal["timestamp"], utc=True)
            entry_idx = bars.index[bars["timestamp"] > s_ts]
            if len(entry_idx) == 0:
                continue
            i = int(entry_idx[0])
            row = bars.iloc[i]
            side = str(signal["side"])
            base_open = float(row["open"])
            slip = self.config.slippage_pct / 100.0
            spread = self.config.spread_bps / 10000.0
            entry_fill = base_open * (1 + slip + spread / 2) if side == "long" else base_open * (1 - slip - spread / 2)

            stop = float(signal["stop_price"])
            target = float(signal["target_price"])
            size = float(signal["size"])
            if size <= 0:
                continue

            exit_price = float(bars.iloc[-1]["close"])
            exit_ts = pd.to_datetime(bars.iloc[-1]["timestamp"], utc=True)
            exit_idx = len(bars) - 1

            initial_risk = abs(entry_fill - stop)
            trailing_stop = stop
            peak = entry_fill
            trough = entry_fill
            for j in range(i, len(bars)):
                b = bars.iloc[j]
                hi = float(b["high"])
                lo = float(b["low"])
                ts = pd.to_datetime(b["timestamp"], utc=True)

                # forced exit before close
                close_h, close_m = map(int, self.config.session_close_utc.split(":"))
                session_close = ts.normalize() + pd.Timedelta(hours=close_h, minutes=close_m)
                force_exit_time = session_close - pd.Timedelta(minutes=self.config.exit_before_close_minutes)
                if ts >= force_exit_time:
                    exit_price = float(b["close"])
                    exit_ts = ts
                    exit_idx = j
                    break

                if self.config.trailing_stop_enabled and initial_risk > 0:
                    if side == "long":
                        peak = max(peak, hi)
                        if (peak - entry_fill) >= self.config.trailing_stop_activation_r * initial_risk:
                            trailing_stop = max(
                                trailing_stop,
                                peak - self.config.trailing_stop_trail_r * initial_risk,
                            )
                    else:
                        trough = min(trough, lo)
                        if (entry_fill - trough) >= self.config.trailing_stop_activation_r * initial_risk:
                            trailing_stop = min(
                                trailing_stop,
                                trough + self.config.trailing_stop_trail_r * initial_risk,
                            )

                stop_to_use = trailing_stop if self.config.trailing_stop_enabled else stop
                if side == "long":
                    if lo <= stop_to_use:
                        exit_price = stop_to_use
                        exit_ts = ts
                        exit_idx = j
                        break
                    if hi >= target:
                        exit_price = target
                        exit_ts = ts
                        exit_idx = j
                        break
                else:
                    if hi >= stop_to_use:
                        exit_price = stop_to_use
                        exit_ts = ts
                        exit_idx = j
                        break
                    if lo <= target:
                        exit_price = target
                        exit_ts = ts
                        exit_idx = j
                        break

            exit_fill = exit_price * (1 - spread / 2) if side == "long" else exit_price * (1 + spread / 2)
            commission = self.config.commission_per_share * size * 2
            gross = (exit_fill - entry_fill) * size if side == "long" else (entry_fill - exit_fill) * size
            net = gross - commission
            realized += net
            equity = self.config.initial_capital + realized

            trades.append(
                {
                    "timestamp": s_ts,
                    "side": side,
                    "entry_fill_price": entry_fill,
                    "exit_price": exit_price,
                    "exit_fill_price": exit_fill,
                    "size": size,
                    "commission_paid": commission,
                    "gross_pnl": gross,
                    "net_pnl": net,
                    "entry_index": i,
                    "exit_index": exit_idx,
                    "entry_time": row["timestamp"],
                    "exit_time": exit_ts,
                    "hold_bars": exit_idx - i,
                }
            )
            logger.info("Executed trade side=%s net_pnl=%.2f", side, net)

        trades_df = pd.DataFrame(trades)
        equity_points = []
        running = self.config.initial_capital
        for k, b in bars.iterrows():
            if not trades_df.empty:
                closed = trades_df[trades_df["exit_index"] == k]
                if not closed.empty:
                    running += float(closed["net_pnl"].sum())
            equity_points.append({"timestamp": b["timestamp"], "equity": running})

        return trades_df, pd.DataFrame(equity_points)
