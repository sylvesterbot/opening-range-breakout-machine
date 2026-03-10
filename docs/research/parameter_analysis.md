# Parameter Sensitivity Analysis

Total combinations evaluated: 48

## Heatmaps
- output/plots/sensitivity_sharpe_heatmap.png
- output/plots/sensitivity_total_return_heatmap.png
- output/plots/sensitivity_max_drawdown_heatmap.png

## Robust Region (positive expectancy cluster)
 orb_window  rr  count
         60 1.0      3
         60 1.5      3
         60 2.0      3
         60 3.0      3

## Sensitivity Ranking
1. Reward:Risk ratio (largest shifts in expectancy across tested grid)
2. ORB window length
3. Risk per trade (scales returns/drawdowns but less impact on directional edge)
