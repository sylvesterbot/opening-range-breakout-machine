from __future__ import annotations

from pathlib import Path

import pandas as pd

from data.cleaner import DataCleaner
from data.fetcher import MarketDataFetcher
from data.storage import ParquetStorage


def _bars(symbol: str) -> pd.DataFrame:
    idx = pd.date_range("2025-01-02 09:30", periods=6, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": [100, 101, 102, 103, 104, 105],
            "high": [101, 102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103, 104],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5],
            "volume": [10, 12, 0, 14, 15, 16],
            "symbol": symbol,
        }
    )


def test_source_agnostic_fetcher_returns_canonical_columns() -> None:
    providers = {"first": lambda **_: _bars("SPY"), "second": lambda **_: _bars("QQQ")}
    fetcher = MarketDataFetcher(providers=providers)

    spy = fetcher.fetch_symbol("SPY", source="first", interval="5m", start="2025-01-02", end="2025-01-02")
    qqq = fetcher.fetch_symbol("QQQ", source="second", interval="5m", start="2025-01-02", end="2025-01-02")

    assert list(spy.columns) == fetcher.CANONICAL_COLUMNS
    assert list(qqq.columns) == fetcher.CANONICAL_COLUMNS
    assert spy["symbol"].iloc[0] == "SPY"
    assert qqq["symbol"].iloc[0] == "QQQ"


def test_fetcher_normalizes_multiindex_columns() -> None:
    tuple_frame = pd.DataFrame(
        {
            ("Open", "SPY"): [1.0],
            ("High", "SPY"): [1.5],
            ("Low", "SPY"): [0.5],
            ("Close", "SPY"): [1.2],
            ("Volume", "SPY"): [100],
        },
        index=pd.DatetimeIndex([pd.Timestamp("2025-01-02 09:30:00", tz="UTC")]),
    ).reset_index().rename(columns={"index": "timestamp"})

    fetcher = MarketDataFetcher(providers={"mock": lambda **_: tuple_frame})
    out = fetcher.fetch_symbol("SPY", source="mock", interval="5m", start="x", end="y")

    assert out["open"].iloc[0] == 1.0
    assert out["close"].iloc[0] == 1.2


def test_cleaner_generates_quality_gap_logs() -> None:
    cleaner = DataCleaner(target_timezone="UTC", session_open="09:30", session_close="16:00")
    raw = _bars("SPY")
    raw = pd.concat([raw, raw.iloc[[1]]], ignore_index=True)  # duplicate

    cleaned, quality = cleaner.clean(raw)

    assert "missing_bars_pct" in quality
    assert quality["duplicate_rows"] >= 1
    assert cleaned["timestamp"].is_monotonic_increasing


def test_parquet_storage_and_cache_behavior(tmp_path: Path) -> None:
    storage = ParquetStorage(cache_dir=tmp_path / "cache", processed_dir=tmp_path / "processed")
    df = _bars("SPY")

    path = storage.save_processed(df, symbol="SPY")
    assert path.exists()

    loaded = storage.load_processed(symbol="SPY", date="2025-01-02")
    assert loaded is not None
    assert len(loaded) == len(df)

    cache_key = "SPY_5m_2025-01-01_2025-01-10_yfinance"
    storage.write_cache(cache_key, df)
    assert storage.is_cached(cache_key)
    cached = storage.read_cache(cache_key)
    assert cached is not None
    assert len(cached) == len(df)
