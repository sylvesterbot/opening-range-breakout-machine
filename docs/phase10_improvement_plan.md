# Phase 10 Improvement Plan — 5-Year Data Expansion & Scientific Backtesting

Date: 2026-03-11

## Scope
This plan covers Phase 10 execution with strict batch gates and experiment tracking.

## 1) Verification of the 6 Known Bugs + Fix Plan

### Bug 1 (Critical): `src/backtest/walk_forward.py` hardcoded `session_open="14:30"`
- **Verified**: `run_walk_forward()` calls `strat.run(... session_open="14:30" ...)` in three places.
- **Impact**: Walk-forward bypasses timezone conversion and can drift with non-default sessions.
- **Fix**:
  1. Add `session_open_utc: str` param to `run_walk_forward()`.
  2. Replace all hardcoded calls with `session_open=session_open_utc`.
  3. Update callers (`scripts/run_experiment.py`) to pass computed UTC session open.

### Bug 2 (Critical): `scripts/run_sensitivity.py` missing risk features in `BacktestConfig`
- **Verified**: sensitivity engine init only passes capital/cost fields; trailing stop + exit-before-close fields are omitted.
- **Impact**: optimization was run on incomplete execution model, invalidating "best" params.
- **Fix**:
  1. Read risk block from strategy config.
  2. Compute `session_close_utc` via helper.
  3. Pass `trailing_stop_enabled`, `trailing_stop_activation_r`, `trailing_stop_trail_r`, `exit_before_close_minutes`, `session_close_utc` into `BacktestConfig`.

### Bug 3 (Critical): `src/backtest/quantstats_mc.py` parsing broken for current QuantStats return object
- **Verified**: current code assumes dict-like payload from `qs.stats.montecarlo()`. Installed version returns `MonteCarloResult` object, so dict parsing yields defaults/zeros.
- **Impact**: bust/goal probabilities and derived MC stats are wrong (zeroed).
- **Fix**:
  1. Parse `MonteCarloResult` attributes (`bust_probability`, `goal_probability`, `data`, `stats`).
  2. Compute MC Sharpe/CAGR distribution from simulation paths with robust fallback if format changes.
  3. Keep manual fallback path for unknown return structure.

### Bug 4 (Moderate): `_session_time_utc` uses `datetime.now()` (DST instability)
- **Verified**: helper in scripts uses `datetime.now(ZoneInfo(...))`.
- **Impact**: same config can produce different UTC open/close depending on execution date.
- **Fix**:
  1. Use midpoint of configured `start_date` and `end_date` as fixed reference date.
  2. Build timezone-aware local datetime on that reference date for conversion.
  3. Apply to all relevant scripts.

### Bug 5 (Moderate): `scripts/run_backtest.py` stale hardcoded/open-time handling
- **Verified**: script still uses old helper behavior with `datetime.now()` and stale session handling pattern.
- **Impact**: backtest script not consistent with experiment runner.
- **Fix**: align with fixed-reference `_session_time_utc()` and current risk-aware engine config pattern.

### Bug 6 (Moderate): Missing unit tests for filters/risk/walk-forward behavior
- **Verified**: tests do not currently cover ATR reject, SMA directional block, trailing activation, exit-before-close, and non-empty WFO windows.
- **Impact**: regressions can slip through and silently alter strategy behavior.
- **Fix**: add 5 targeted tests with deterministic synthetic data fixtures.

## 2) Dependency Graph Between Batches

1. **Batch 0 must complete first**
   - Required to correct execution semantics and remove invalid baseline artifacts.
   - Batch 1/2/3 results are not trustworthy if Batch 0 remains unfixed.
2. **Batch 1 (5-year data) depends on Batch 0**
   - Data expansion should run on corrected session/risk logic.
3. **Batch 2 (Advanced MC) depends on Batch 1**
   - Needs larger sample size for robust CI/PSR/regime analysis.
4. **Batch 3 (Scientific validation) depends on Batch 2**
   - Uses upgraded MC + stable WFO behavior.
5. **Batch 4 final report depends on all prior batches**
   - Final synthesis requires completed experiments 008–012.

## 3) Risk Assessment by Change

- **Walk-forward session parameterization**: *Low risk*
  - Localized API change; potential caller mismatch risk mitigated by type hints/tests.
- **Sensitivity risk-feature injection**: *Medium risk*
  - Will intentionally change optimization surface and outputs.
- **QuantStats return parsing rewrite**: *Medium-High risk*
  - Third-party API format variability; mitigated via compatibility parsing + fallback.
- **DST fixed-reference conversion**: *Low-Medium risk*
  - Date conversion behavior changes globally; verify with deterministic tests.
- **run_backtest alignment**: *Low risk*
  - Script-only consistency fix.
- **New unit tests**: *Low risk*
  - Adds coverage; may expose latent defects (desired behavior).

## 4) 5-Year Data Volume Estimates (SPY/QQQ/IWM)

Assumptions:
- 5-minute bars
- 78 regular-session bars/day
- ~252 trading days/year
- 3 symbols

Estimates:
- Bars per symbol/year: `78 × 252 = 19,656`
- Bars per symbol/5 years: `19,656 × 5 = 98,280`
- Total bars for 3 symbols: `98,280 × 3 = 294,840`

Storage rough order-of-magnitude:
- Parquet compressed numeric OHLCV dataset for ~295k rows is expected in tens of MB (schema dependent).

## Batch 0 execution order (first gate)
1. Fix walk-forward hardcoding + pass dynamic session open.
2. Fix sensitivity script to include full risk features.
3. Fix QuantStats MC parsing and fallback.
4. Then implement DST fix, stale backtest script fix, and missing tests.
5. Run sensitivity + `experiment_008` + full tests.

## Batch 0 closeout status (evidence)
- [x] Bug 1 fixed: `src/backtest/walk_forward.py` now accepts `session_open_utc` and no longer hardcodes `14:30`.
- [x] Bug 2 fixed: `scripts/run_sensitivity.py` now passes full risk/trailing/session-close settings to `BacktestConfig`.
- [x] Bug 3 fixed: `src/backtest/quantstats_mc.py` handles `MonteCarloResult` + fallback formats robustly.
- [ ] Bug 4 planned for next batch workstream (fixed-date conversion hardening already tracked; requires broader script sweep).
- [ ] Bug 5 planned for next batch workstream (run_backtest alignment tracked).
- [ ] Bug 6 planned for next batch workstream (additional dedicated tests tracked).

Batch 0 gate evidence collected:
- Tests: `uv run python -m pytest -q` -> `19 passed, 1 warning`.
- Experiment baseline/comparison: `experiment_009` generated (auto-increment from reruns) with report at
  `output/experiment_reports/exp_experiment_009_report.md`, compared vs `experiment_008`.
