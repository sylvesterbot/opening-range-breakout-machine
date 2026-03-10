# opening-range-breakout-machine

Opening Range Breakout (ORB) research + backtesting project with strict phase gates.

## Environment (uv-only)

```bash
uv sync
uv sync --extra dev
```

Python version is pinned in `.python-version`.

## Credentials

Alpaca credentials are optional when using yfinance fallback. For Alpaca primary:

```bash
# in project root .env (preferred) or exported env vars
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
```

`.env` is git-ignored and must never be committed.

## Data Source Behavior

Configured in `config/backtest_config.yaml`:

```yaml
data:
  source: "alpaca"
  fallback_source: "yfinance"
```

The fetcher is source-agnostic and automatically falls back if primary source errors/returns empty.

## Runbook

```bash
# 1) Fetch/clean/cache/parquet
uv run python scripts/fetch_data.py

# 2) ORB backtest (Phase 5)
uv run python scripts/run_backtest.py

# 3) Monte Carlo robustness (Phase 6)
uv run python scripts/run_monte_carlo.py

# 4) Parameter sensitivity grid (Phase 7)
uv run python scripts/run_sensitivity.py

# 5) Tests
uv run python -m pytest tests/test_data_pipeline.py -v
uv run python -m pytest tests/test_orb_strategy.py -v
uv run python -m pytest tests/test_backtest_engine.py -v
uv run python -m pytest tests/test_monte_carlo.py -v
```

## Troubleshooting

- If `uv run pytest ...` fails to spawn in your environment, use:
  - `uv run python -m pytest ...`
- If Alpaca auth fails, verify `.env` is loaded and keys are valid.
- If cache shape looks stale, remove relevant files in `data/cache/` and rerun fetch.

## Phase Gate Traceability

- Phase 1: research docs in `docs/research/`
- Phase 2: strategy rules in `docs/strategy_blueprint.md`
- Phase 3: data pipeline in `src/data/`
- Phase 4: strategy modules in `src/strategy/`
- Phase 5: backtest engine/metrics in `src/backtest/` + `scripts/run_backtest.py`
- Phase 6: Monte Carlo in `src/backtest/monte_carlo.py` + `scripts/run_monte_carlo.py`
- Phase 7: sensitivity + heatmaps in `scripts/run_sensitivity.py` and `docs/research/parameter_analysis.md`
