"""Data cleaning and quality metrics for intraday bars."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DataCleaner:
    """Cleans intraday bars and computes quality diagnostics."""

    target_timezone: str
    session_open: str
    session_close: str

    def clean(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
        """Clean a dataframe and return cleaned bars plus quality metrics."""
        if frame.empty:
            return frame.copy(), self._quality(0, 0, 0, 0)

        df = frame.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"])

        before = len(df)
        duplicates = int(df.duplicated(subset=["timestamp", "symbol"]).sum())
        df = df.drop_duplicates(subset=["timestamp", "symbol"], keep="first")

        df = df.sort_values("timestamp")
        try:
            df["timestamp"] = df["timestamp"].dt.tz_convert(self.target_timezone)
        except Exception:
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

        session_df = self._session_filter(df)
        zero_volume = int((session_df["volume"] <= 0).sum()) if "volume" in session_df.columns else 0
        missing_pct = self._missing_pct(session_df)

        quality = self._quality(
            total_rows=before,
            duplicate_rows=duplicates,
            zero_volume_rows=zero_volume,
            missing_bars_pct=missing_pct,
        )
        return session_df.reset_index(drop=True), quality

    def _session_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.set_index("timestamp").between_time(self.session_open, self.session_close).reset_index()

    def _missing_pct(self, df: pd.DataFrame) -> float:
        if len(df) < 2:
            return 0.0
        inferred = pd.infer_freq(df["timestamp"])
        if inferred is None:
            inferred = "5min"
        expected = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq=inferred, tz=df["timestamp"].dt.tz)
        missing = max(len(expected) - len(df), 0)
        return round((missing / max(len(expected), 1)) * 100.0, 4)

    @staticmethod
    def _quality(total_rows: int, duplicate_rows: int, zero_volume_rows: int, missing_bars_pct: float) -> dict[str, float]:
        return {
            "total_rows": float(total_rows),
            "duplicate_rows": float(duplicate_rows),
            "zero_volume_rows": float(zero_volume_rows),
            "missing_bars_pct": float(missing_bars_pct),
        }
