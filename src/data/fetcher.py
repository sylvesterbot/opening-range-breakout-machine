"""Source-agnostic market data fetcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


ProviderFn = Callable[..., pd.DataFrame]


@dataclass
class MarketDataFetcher:
    """Fetches bars from multiple providers and normalizes to a canonical schema."""

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
            self.providers = {"yfinance": self._fetch_yfinance}

    def fetch_symbol(
        self,
        symbol: str,
        source: str,
        interval: str,
        start: str,
        end: str,
        asset_class: str = "equity",
    ) -> pd.DataFrame:
        """Fetch bars for one symbol and return canonical frame."""
        if source not in self.providers:
            raise ValueError(f"Unsupported source: {source}")

        frame = self.providers[source](symbol=symbol, interval=interval, start=start, end=end)
        if frame.empty:
            return pd.DataFrame(columns=self.CANONICAL_COLUMNS)

        normalized = self._normalize(frame=frame, symbol=symbol, source=source, asset_class=asset_class)
        return normalized[self.CANONICAL_COLUMNS].sort_values("timestamp").reset_index(drop=True)

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
