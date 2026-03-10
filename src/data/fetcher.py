"""Source-agnostic market data fetcher with optional provider fallback."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable

import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
except Exception:  # pragma: no cover
    StockHistoricalDataClient = None
    StockBarsRequest = None
    TimeFrame = None


logger = logging.getLogger(__name__)
ProviderFn = Callable[..., pd.DataFrame]


@dataclass
class MarketDataFetcher:
    """Fetch bars from multiple providers and normalize to canonical schema."""

    providers: dict[str, ProviderFn] | None = None

    CANONICAL_COLUMNS = [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "asset_class",
    ]

    def __post_init__(self) -> None:
        if self.providers is None:
            self.providers = {
                "alpaca": self._fetch_alpaca,
                "yfinance": self._fetch_yfinance,
            }

    def fetch_symbol(
        self,
        symbol: str,
        source: str,
        interval: str,
        start: str,
        end: str,
        asset_class: str = "equity",
        fallback_source: str | None = None,
    ) -> pd.DataFrame:
        """Fetch bars for one symbol and return canonical frame.

        Attempts primary source first, then optional fallback source.
        """
        frame, used_source = self._fetch_with_optional_fallback(
            symbol=symbol,
            source=source,
            interval=interval,
            start=start,
            end=end,
            fallback_source=fallback_source,
        )
        if frame.empty:
            return pd.DataFrame(columns=self.CANONICAL_COLUMNS)

        normalized = self._normalize(frame=frame, symbol=symbol, source=used_source, asset_class=asset_class)
        return normalized[self.CANONICAL_COLUMNS].sort_values("timestamp").reset_index(drop=True)

    def _fetch_with_optional_fallback(
        self,
        symbol: str,
        source: str,
        interval: str,
        start: str,
        end: str,
        fallback_source: str | None,
    ) -> tuple[pd.DataFrame, str]:
        if source not in self.providers:
            raise ValueError(f"Unsupported source: {source}")

        try:
            primary = self.providers[source](symbol=symbol, interval=interval, start=start, end=end)
            if not primary.empty:
                return primary, source
            logger.warning("Primary source returned empty frame: %s", source)
        except Exception as exc:
            logger.warning("Primary source failed (%s): %s", source, exc)

        if fallback_source:
            if fallback_source not in self.providers:
                raise ValueError(f"Unsupported fallback source: {fallback_source}")
            logger.info("Trying fallback source %s for %s", fallback_source, symbol)
            fallback_frame = self.providers[fallback_source](symbol=symbol, interval=interval, start=start, end=end)
            return fallback_frame, fallback_source

        return pd.DataFrame(), source

    def _fetch_alpaca(self, symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
        if StockHistoricalDataClient is None or StockBarsRequest is None:
            raise RuntimeError("alpaca-py is not available in the environment")

        key = os.getenv("APCA_API_KEY_ID")
        secret = os.getenv("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Missing Alpaca credentials in env: APCA_API_KEY_ID/APCA_API_SECRET_KEY")

        timeframe = self._interval_to_alpaca_timeframe(interval)
        client = StockHistoricalDataClient(api_key=key, secret_key=secret)
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=timeframe, start=start, end=end)
        bars = client.get_stock_bars(request).df
        if bars.empty:
            return pd.DataFrame()
        bars = bars.reset_index().rename(columns={"timestamp": "timestamp"})
        return bars

    def _fetch_yfinance(self, symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
        if yf is None:
            raise RuntimeError("yfinance is not available in the environment")
        bars = yf.download(symbol, interval=interval, start=start, end=end, progress=False, auto_adjust=False)
        if bars.empty:
            return pd.DataFrame()
        bars = bars.reset_index().rename(columns={"Datetime": "timestamp", "Date": "timestamp"})
        bars.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in bars.columns]
        if "adj close" in bars.columns:
            bars = bars.drop(columns=["adj close"])
        return bars

    def _normalize(self, frame: pd.DataFrame, symbol: str, source: str, asset_class: str) -> pd.DataFrame:
        out = frame.copy()
        out.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in out.columns]
        if "timestamp" not in out.columns:
            raise ValueError("Provider output missing timestamp column")

        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in out.columns:
                out[col] = 0.0
        out["symbol"] = symbol
        out["source"] = source
        out["asset_class"] = asset_class
        return out

    @staticmethod
    def _interval_to_alpaca_timeframe(interval: str) -> TimeFrame:
        mapping = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame(5, TimeFrame.Minute.unit),
            "15m": TimeFrame(15, TimeFrame.Minute.unit),
            "1h": TimeFrame.Hour,
        }
        if interval not in mapping:
            raise ValueError(f"Unsupported interval for Alpaca: {interval}")
        return mapping[interval]
