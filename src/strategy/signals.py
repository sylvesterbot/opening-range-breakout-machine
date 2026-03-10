"""Signal generation for Opening Range Breakout strategy."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol"]


def generate_orb_signals(
    bars: pd.DataFrame,
    opening_range_minutes: int,
    session_open: str,
    entry_window_hours: int,
    entry_confirmation: str,
    volume_threshold_multiplier: float,
    max_entries_per_day: int,
) -> pd.DataFrame:
    """Generate ORB entry signals from intraday bars.

    Args:
        bars: Canonical intraday bars.
        opening_range_minutes: Opening range lookback in minutes.
        session_open: Session open in HH:MM.
        entry_window_hours: Max hours after open for entries.
        entry_confirmation: One of close|volume|both.
        volume_threshold_multiplier: Volume threshold multiplier.
        max_entries_per_day: Max entries per direction per day.

    Returns:
        DataFrame with signal rows.
    """
    if bars.empty:
        return pd.DataFrame(columns=["timestamp", "symbol", "side", "entry_price", "or_high", "or_low"])

    for col in REQUIRED_COLUMNS:
        if col not in bars.columns:
            raise ValueError(f"Missing column: {col}")

    df = bars.copy().sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    out: list[dict[str, object]] = []

    for _, day in df.groupby(df["timestamp"].dt.date):
        day = day.copy()
        day_start = pd.Timestamp(f"{day['timestamp'].iloc[0].date()} {session_open}", tz="UTC")
        or_end = day_start + pd.Timedelta(minutes=opening_range_minutes)
        entry_end = day_start + pd.Timedelta(hours=entry_window_hours)

        or_slice = day[(day["timestamp"] >= day_start) & (day["timestamp"] < or_end)]
        if or_slice.empty:
            continue

        or_high = float(or_slice["high"].max())
        or_low = float(or_slice["low"].min())
        avg_vol = float(or_slice["volume"].mean())

        long_count = 0
        short_count = 0
        candidates = day[(day["timestamp"] >= or_end) & (day["timestamp"] <= entry_end)]
        for _, row in candidates.iterrows():
            close_confirm_long = row["close"] > or_high
            close_confirm_short = row["close"] < or_low
            vol_confirm = row["volume"] >= (avg_vol * volume_threshold_multiplier)

            long_ok = _entry_ok(entry_confirmation, close_confirm_long, vol_confirm)
            short_ok = _entry_ok(entry_confirmation, close_confirm_short, vol_confirm)

            if long_ok and long_count < max_entries_per_day:
                out.append(
                    {
                        "timestamp": row["timestamp"],
                        "symbol": row["symbol"],
                        "side": "long",
                        "entry_price": float(row["close"]),
                        "or_high": or_high,
                        "or_low": or_low,
                    }
                )
                long_count += 1

            if short_ok and short_count < max_entries_per_day:
                out.append(
                    {
                        "timestamp": row["timestamp"],
                        "symbol": row["symbol"],
                        "side": "short",
                        "entry_price": float(row["close"]),
                        "or_high": or_high,
                        "or_low": or_low,
                    }
                )
                short_count += 1

    return pd.DataFrame(out)


def _entry_ok(mode: str, close_cond: bool, vol_cond: bool) -> bool:
    if mode == "close":
        return close_cond
    if mode == "volume":
        return vol_cond
    if mode == "both":
        return close_cond and vol_cond
    raise ValueError(f"Unsupported entry_confirmation: {mode}")
