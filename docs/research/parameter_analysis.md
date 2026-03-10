# Parameter Sensitivity Analysis

Total combinations evaluated: 48

Results CSV: output/backtests/sensitivity_results.csv

## Heatmaps
- output/plots/sensitivity_sharpe_heatmap.png
- output/plots/sensitivity_total_return_heatmap.png
- output/plots/sensitivity_max_drawdown_heatmap.png

## Best Config (composite score)
best_orb_window: 60.0
best_rr: 2.0
best_risk_pct: 1.0
best_score: 6.296063111056718

Promoted to:
- config/best_config.yaml
- config/strategy_params.yaml

## Robust Region (positive expectancy cluster)
 orb_window  rr  count
          5 1.0      3
          5 1.5      3
          5 2.0      3
          5 3.0      3
         15 1.0      3
         15 1.5      3
         15 2.0      3
         15 3.0      3
         30 1.0      3
         30 1.5      3

## Sensitivity Ranking
1. Reward:Risk ratio
2. ORB window length
3. Risk per trade
