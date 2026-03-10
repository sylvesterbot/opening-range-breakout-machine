# Phase 9 Improvement Plan

## I'm using the executing-plans skill to implement this plan.

## 1) Current Codebase Gap Analysis

### Data + Config
- `config/backtest_config.yaml` uses short date range by default in prior phases; statistically weak for ORB inference.
- `scripts/run_backtest.py` currently passes a fixed session open (`"14:30"`), not computed from session profile + timezone.

### Strategy Layer
- `src/strategy/signals.py` currently generates breakout signals but does not apply configured ATR range or trend SMA filters.
- `src/strategy/orb.py` does not fully pass/activate filter controls from YAML.

### Backtest Engine
- `src/backtest/engine.py` includes costs/slippage/spread and fill assumptions, but lacks risk features configured in YAML:
  - trailing stop activation + trail logic
  - force exit before close by configured minutes

### Experimentation/Scientific Workflow
- No structured experiment log exists yet.
- No automatic comparison/delta engine for before/after runs.
- No single experiment runner that stitches fetch/backtest/MC/logging/comparison/report.

### Validation & Reporting
- Sensitivity script exists but is not yet integrated with experiment tracker as sub-experiments.
- No walk-forward validation module.
- No quantstats integration / tear-sheet.
- No multi-symbol portfolio synthesis report with experiment history rollup.

## 2) Dependency Graph (Batch Order)

1. **Batch 0 first**: experiment tracking infra (`tracker`, `comparator`, `run_experiment`) is foundational.
2. **Batch 1 next**: data expansion and session-open config bug fix; required before evaluating feature improvements.
3. **Batch 2**: strategy/backtest missing features (ATR/SMA filters + trailing + exit-before-close).
4. **Batch 3**: sensitivity/optimization depends on Batch 2 feature-complete behavior.
5. **Batch 4**: quantstats + walk-forward depends on stable optimized pipeline from Batch 3.
6. **Batch 5**: portfolio + final report depends on all prior outputs and experiment history.

## 3) Risk Assessment

| Change | Risk | Why | Mitigation |
|---|---|---|---|
| Tracker/comparator logging | Low | Isolated modules, append-only IO | Unit tests for comparator and tracker load/append |
| Dynamic session-open conversion | Medium | Timezone conversion bugs can silently distort entries | Add deterministic tests and log computed UTC session open |
| ATR + SMA filters | Medium | Could over-filter and produce zero trades | Add signal-count logs, unit tests on synthetic bars |
| Trailing stop + exit-before-close | High | Stateful trade lifecycle changes, easy off-by-one errors | Add focused engine tests with explicit expected exits |
| 48-grid sensitivity + promotion | Medium | Runtime and selection logic complexity | Persist per-combo metrics + deterministic score formula |
| QuantStats + walk-forward | High | New dependency + heavier pipeline | Add guarded fallback checks and isolated validation tests |
| Portfolio aggregation/report | Medium | Aggregation math/correlation edge cases | Validate with per-symbol sanity checks before portfolio combine |

## 4) Expected Impact Ranking

1. **Data range expansion (Batch 1)** — largest impact (sample size/trade count validity).
2. **ATR/SMA filters (Batch 2)** — likely strongest edge-quality improvement by reducing false breakouts.
3. **Exit-before-close + trailing (Batch 2)** — risk-adjusted improvements expected.
4. **Parameter optimization (Batch 3)** — improves calibration if not overfit.
5. **Walk-forward validation (Batch 4)** — mostly confidence/robustness, not direct edge creation.
6. **Portfolio expansion (Batch 5)** — diversification impact on aggregate metrics.

## Gate Discipline
- Each batch ends with:
  1) acceptance checklist,
  2) uv command outputs,
  3) experiment id and comparison delta,
  4) descriptive git commit.
