# ORB Execution Plan

## Think-Before-You-Code Reasoning Steps

1. Define atomic ORB rule components first (session detection, opening range calc, breakout validation, position sizing, exits) so each unit can be independently tested.
2. Standardize a canonical bar schema (`timestamp, symbol, open, high, low, close, volume, source, asset_class`) to keep fetcher source-agnostic.
3. Build ingestion adapters per provider (Alpaca, yfinance, Dukascopy, HistData) and normalize immediately into canonical schema.
4. Apply cleaning pipeline in fixed order: timezone normalization -> duplicate removal -> missing-bar detection -> session filtering -> quality scoring.
5. Persist processed bars in Parquet partitioned by `symbol/date` and track metadata in sidecar JSON for cache freshness and provenance.
6. Define strategy blueprint math before coding signals: OR high/low over first N minutes, entry confirmation modes, risk unit `R`, and time exits.
7. Implement backtest fill model explicitly (next-bar open fill) with commission/slippage applied at order fill level to avoid overstated performance.
8. Compute trade ledger first, then derive equity curve and metrics from ledger so Monte Carlo can reuse trade-return distribution.
9. Design Monte Carlo as trade-level bootstrap with replacement, slippage perturbation, and convergence monitoring every 500 iterations.
10. Add deterministic random seed controls and reproducibility hooks for all simulations and sensitivity runs.
11. Run parameter grid (48 combos) after base validation; prioritize robust regions (clusters) over single best parameters to reduce overfitting risk.
12. Enforce phase gates by tests + documentation + git commit per phase, with explicit linkage from implementation decisions to research citations.

## Module Dependency Graph

- `src/data/*` -> used by `src/strategy/*` and `src/backtest/*`
- `src/strategy/*` -> produces signals/trades for `src/backtest/engine.py`
- `src/backtest/metrics.py` -> consumes equity/trade ledger
- `src/backtest/monte_carlo.py` -> consumes trade returns
- `src/visualization/*` -> consumes backtest + MC outputs
- `scripts/*` -> orchestrate config loading and module calls

## Phase Gate Checklist

Each phase requires:
- acceptance criteria checkboxes satisfied,
- relevant test command output captured,
- docs updated,
- git commit pushed.
