"""Fetch, clean, and store market data from configured source."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from data.cleaner import DataCleaner
from data.fetcher import MarketDataFetcher
from data.storage import ParquetStorage


def main() -> None:
    load_dotenv()
    config = yaml.safe_load(Path("config/backtest_config.yaml").read_text(encoding="utf-8"))
    data_cfg = config["data"]
    session_cfg = config["sessions"]["equity"]

    fetcher = MarketDataFetcher()
    cleaner = DataCleaner(
        target_timezone=data_cfg.get("timezone", "UTC"),
        session_open=session_cfg["open"],
        session_close=session_cfg["close"],
    )
    storage = ParquetStorage(
        cache_dir=Path(data_cfg.get("cache_dir", "data/cache")),
        processed_dir=Path(data_cfg.get("processed_dir", "data/processed")),
    )

    for symbol in data_cfg["symbols"]:
        key = f"{symbol}_{data_cfg['interval']}_{data_cfg['start_date']}_{data_cfg['end_date']}_{data_cfg['source']}"
        if storage.is_cached(key):
            raw = storage.read_cache(key)
            cache_state = "HIT"
        else:
            raw = fetcher.fetch_symbol(
                symbol=symbol,
                source=data_cfg["source"],
                interval=data_cfg["interval"],
                start=data_cfg["start_date"],
                end=data_cfg["end_date"],
                asset_class=data_cfg["asset_class"],
                fallback_source=data_cfg.get("fallback_source"),
            )
            storage.write_cache(key, raw)
            cache_state = "MISS->WRITE"

        cleaned, quality = cleaner.clean(raw)
        path = storage.save_processed(cleaned, symbol=symbol)
        print(f"{symbol} cache={cache_state} rows={len(cleaned)} parquet={path}")
        print(f"{symbol} quality={quality}")


if __name__ == "__main__":
    main()
