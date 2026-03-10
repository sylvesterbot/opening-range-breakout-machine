# opening-range-breakout-machine

## Data source configuration (equities)

Primary source is configured in `config/backtest_config.yaml`:

```yaml
data:
  source: "alpaca"
  fallback_source: "yfinance"
```

The fetcher uses a source-agnostic output schema and will:
1. try `source` first,
2. if the source errors or returns empty, automatically try `fallback_source`.

## Alpaca credentials

Set credentials via environment variables (or project-root `.env`; `scripts/fetch_data.py` auto-loads it):

```bash
export APCA_API_KEY_ID="..."
export APCA_API_SECRET_KEY="..."
```

Do not share credentials in chat.

## Commands (uv only)

```bash
uv sync --extra dev
uv run python scripts/fetch_data.py
uv run pytest tests/test_data_pipeline.py -v
```
