# Opening Range Breakout Machine

A research-to-implementation pipeline for an Opening Range Breakout (ORB) trading strategy, built with strict phase gates, uv-only environment management, reproducible configs, and test coverage.

---

## 1) Project Purpose

This project is designed to:
- research ORB assumptions,
- define rules mathematically,
- fetch/clean/cache intraday data,
- run backtests with realistic costs,
- stress test via Monte Carlo,
- test parameter robustness via sensitivity grids.

It supports **equities first** with **Alpaca primary + yfinance fallback**.

---

## 2) High-Level Architecture

```text
config/*.yaml
    |
    v
scripts/fetch_data.py -----> src/data/fetcher.py -----> src/data/cleaner.py -----> src/data/storage.py
                                                                               |-> data/cache/*.parquet
                                                                               |-> data/processed/symbol=*/date=*/bars.parquet

scripts/run_backtest.py ---> src/strategy/* + src/backtest/engine.py + src/backtest/metrics.py
                           |-> output/plots/equity_curve.png

scripts/run_monte_carlo.py -> src/backtest/monte_carlo.py + src/visualization/monte_carlo_plots.py
                           |-> output/plots/mc_*.png

scripts/run_sensitivity.py -> grid search over strategy params + backtest metrics
                           |-> output/plots/sensitivity_*.png
                           |-> docs/research/parameter_analysis.md
```

---

## 3) Repository Layout

- `config/`
  - `backtest_config.yaml`
  - `strategy_params.yaml`
  - `monte_carlo_config.yaml`
- `src/data/`
  - `fetcher.py`, `cleaner.py`, `storage.py`
- `src/strategy/`
  - `signals.py`, `orb.py`, `position_sizing.py`
- `src/backtest/`
  - `engine.py`, `metrics.py`, `monte_carlo.py`
- `src/visualization/`
  - `equity_curve.py`, `monte_carlo_plots.py`
- `scripts/`
  - `fetch_data.py`, `run_backtest.py`, `run_monte_carlo.py`, `run_sensitivity.py`
- `tests/`
  - `test_data_pipeline.py`, `test_orb_strategy.py`, `test_backtest_engine.py`, `test_monte_carlo.py`
- `docs/research/`
  - `orb_research_report.md`, `academic_papers.md`, `parameter_analysis.md`

---

## 4) Setup (uv-only)

### Requirements
- `uv` installed
- Python pinned by `.python-version`

### Install
```bash
uv sync --extra dev
```

> No pip/venv/conda workflow is required or used.

---

## 5) Environment Variables + Security

Create `.env` in project root:

```bash
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
```

Security notes:
- `.env` is git-ignored and must not be committed.
- Never paste API keys in chat, issue comments, or logs.
- If keys are rotated, just update `.env` and rerun fetch.

---

## 6) Data Source Behavior

Configured in `config/backtest_config.yaml`:

```yaml
data:
  source: "alpaca"
  fallback_source: "yfinance"
```

Behavior:
1. Try `source` first.
2. If source fails/returns empty, auto-fallback to `fallback_source`.
3. Normalize to canonical schema:
   - `timestamp, symbol, open, high, low, close, volume, source, asset_class`

### Optional yfinance-only mode (if no Alpaca keys)
Set:

```yaml
data:
  source: "yfinance"
  fallback_source: "yfinance"
```

---

## 7) Single Runbook (Clean Clone → Full Outputs)

```bash
git clone https://github.com/sylvesterbot/opening-range-breakout-machine.git
cd opening-range-breakout-machine

uv sync --extra dev

# optional: create .env for Alpaca
cat > .env <<'EOF'
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
EOF

# run full pipeline
uv run python scripts/fetch_data.py
uv run python scripts/run_backtest.py
uv run python scripts/run_monte_carlo.py
uv run python scripts/run_sensitivity.py

# run tests
uv run python -m pytest tests/ -v
```

---

## 8) Expected Outputs (Artifacts)

### Data
- Cache: `data/cache/*.parquet`
- Processed bars: `data/processed/symbol=*/date=*/bars.parquet`

### Backtest
- Equity curve: `output/plots/equity_curve.png`

### Monte Carlo
- `output/plots/mc_terminal_equity_hist.png`
- `output/plots/mc_equity_fan_chart.png`
- `output/plots/mc_drawdown_hist.png`
- `output/plots/mc_convergence.png`

### Sensitivity
- `output/plots/sensitivity_sharpe_heatmap.png`
- `output/plots/sensitivity_total_return_heatmap.png`
- `output/plots/sensitivity_max_drawdown_heatmap.png`
- `docs/research/parameter_analysis.md`

---

## 9) Phase-by-Phase Deliverables Map

- **Phase 1 (Research):** `docs/research/orb_research_report.md`, `docs/research/academic_papers.md`
- **Phase 2 (Blueprint):** `docs/strategy_blueprint.md`
- **Phase 3 (Data):** `src/data/*`, `scripts/fetch_data.py`, `tests/test_data_pipeline.py`
- **Phase 4 (Strategy):** `src/strategy/*`, `config/strategy_params.yaml`, `tests/test_orb_strategy.py`
- **Phase 5 (Backtest):** `src/backtest/engine.py`, `src/backtest/metrics.py`, `scripts/run_backtest.py`, `tests/test_backtest_engine.py`
- **Phase 6 (Monte Carlo):** `src/backtest/monte_carlo.py`, `src/visualization/monte_carlo_plots.py`, `scripts/run_monte_carlo.py`, `tests/test_monte_carlo.py`
- **Phase 7 (Sensitivity):** `scripts/run_sensitivity.py`, `docs/research/parameter_analysis.md`
- **Phase 8 (Guide/Env):** this README + uv runbook/troubleshooting updates

---

## 10) Metrics and Benchmark Interpretation

Backtest metrics include:
- total return, CAGR,
- Sharpe/Sortino/Calmar,
- max drawdown,
- win rate,
- profit factor,
- avg win/avg loss,
- expectancy,
- total trades,
- average trade duration.

Benchmark comparison:
- `benchmark_buy_hold_return` compares strategy span to buy-and-hold SPY.

Interpretation tips:
- Negative expectancy + low profit factor indicates weak edge in tested period.
- Monte Carlo percentiles estimate outcome dispersion under resampled trade sequences.
- Sensitivity heatmaps help identify robust parameter regions (not single-point overfit).

---

## 11) Troubleshooting

### `uv` missing
Install:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Alpaca key errors
- Ensure `.env` exists in project root.
- Ensure keys are valid and not quoted with stray spaces.
- Switch to yfinance-only mode if needed.

### `uv run pytest ...` launcher quirk
In some environments, direct launcher may fail. Use:
```bash
uv run python -m pytest tests/ -v
```

### Cache confusion
If provider/date settings changed, clear relevant cache files:
```bash
rm -f data/cache/*.parquet
```
Then rerun fetch.

---

## 12) Reproducibility Notes and Current Limitations

Reproducibility:
- Config-driven parameters and deterministic seeds (`monte_carlo_config.yaml`) improve repeatability.
- `uv.lock` pins dependency graph.

Limitations (current state):
- Results depend on selected date window and available intraday bars.
- Strategy is currently baseline ORB; not yet production execution code.
- Monte Carlo operates on backtest trade-level PnL bootstrap assumptions.
- Sensitivity ranking is empirical over current test grid; not universal market truth.

---

## 13) Quick Verification Checklist

```bash
uv run python scripts/fetch_data.py
uv run python scripts/run_backtest.py
uv run python scripts/run_monte_carlo.py
uv run python scripts/run_sensitivity.py
uv run python -m pytest tests/ -v
```

If all commands run and artifacts appear in `output/plots/` + docs update in `docs/research/`, system is functioning end-to-end.
