"""Parquet storage and cache utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


@dataclass
class ParquetStorage:
    """Handles cache-first reads/writes for processed intraday data."""

    cache_dir: Path
    processed_dir: Path

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def save_processed(self, frame: pd.DataFrame, symbol: str) -> Path:
        """Persist processed bars into symbol/date parquet partition."""
        if frame.empty:
            raise ValueError("Cannot persist empty frame")
        df = frame.copy()
        df["date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d")
        date = df["date"].iloc[0]
        folder = self.processed_dir / f"symbol={symbol}" / f"date={date}"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "bars.parquet"
        df.drop(columns=["date"]).to_parquet(target, index=False)
        source = str(df["source"].iloc[0]) if "source" in df.columns else "unknown"
        self._write_metadata(target.with_suffix(".json"), symbol=symbol, source=source, date=date)
        return target

    def load_processed(self, symbol: str, date: str) -> pd.DataFrame | None:
        """Load partitioned processed bars."""
        path = self.processed_dir / f"symbol={symbol}" / f"date={date}" / "bars.parquet"
        if not path.exists():
            return None
        return pd.read_parquet(path)

    def cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.parquet"

    def is_cached(self, cache_key: str) -> bool:
        return self.cache_path(cache_key).exists()

    def write_cache(self, cache_key: str, frame: pd.DataFrame) -> Path:
        path = self.cache_path(cache_key)
        frame.to_parquet(path, index=False)
        return path

    def read_cache(self, cache_key: str) -> pd.DataFrame | None:
        path = self.cache_path(cache_key)
        if not path.exists():
            return None
        return pd.read_parquet(path)

    def _write_metadata(self, metadata_path: Path, symbol: str, source: str, date: str) -> None:
        payload = {
            "symbol": symbol,
            "source": source,
            "date": date,
            "downloaded_at": datetime.now(UTC).isoformat(),
        }
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
