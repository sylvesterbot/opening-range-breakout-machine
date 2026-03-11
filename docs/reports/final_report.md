# Final Report (Batch 5)

Experiment ID: experiment_007
Tearsheet: output/reports/tearsheet.html

## Per-Symbol Metrics
### SPY
- total_return: 0.004434009587451104
- cagr: 0.001556161445800619
- sharpe_ratio: 0.5096347138259734
- sortino_ratio: 0.0256906113757238
- calmar_ratio: 0.2748851303768205
- max_drawdown: -0.005661133593029888
- win_rate: 0.6285714285714286
- profit_factor: 1.3135805995370315
- avg_win_avg_loss: 0.7762067179082458
- expectancy: 6.334299410644537
- total_trades: 70.0
- avg_trade_duration_bars: 46.92857142857143
### QQQ
- total_return: -0.0006506361840797892
- cagr: -0.00022767760175168572
- sharpe_ratio: -0.06184531538068341
- sortino_ratio: -0.0038723724501957043
- calmar_ratio: -0.03945781524031925
- max_drawdown: -0.005770152259191419
- win_rate: 0.4931506849315068
- profit_factor: 0.9682059421969551
- avg_win_avg_loss: 0.9951005517024261
- expectancy: -0.8912824439450944
- total_trades: 73.0
- avg_trade_duration_bars: 49.178082191780824
### IWM
- total_return: 0.007402511652583099
- cagr: 0.0026510325426980508
- sharpe_ratio: 0.5909450383337826
- sortino_ratio: 0.029384381353239696
- calmar_ratio: 0.6471760085291184
- max_drawdown: -0.004096308435047269
- win_rate: 0.5789473684210527
- profit_factor: 1.3334511708752999
- avg_win_avg_loss: 0.9697826697274908
- expectancy: 9.74014691129371
- total_trades: 76.0
- avg_trade_duration_bars: 49.03947368421053

## Portfolio Metrics (Equal Weight)
- total_return: 0.003733317731850816
- cagr: 0.0013009298576627248
- sharpe_ratio: 0.4992592248630535
- sortino_ratio: 0.03773409685169608
- calmar_ratio: 0.34224886006445765
- max_drawdown: -0.0038011225440391927
- win_rate: 0.5662100456621004
- profit_factor: 1.1969217533861682
- avg_win_avg_loss: 0.9169965046103709
- expectancy: 5.107710071212086
- total_trades: 219.0
- avg_trade_duration_bars: 48.41095890410959

## Equity Correlation
          SPY       QQQ       IWM
SPY  1.000000  0.270962  0.380742
QQQ  0.270962  1.000000  0.108174
IWM  0.380742  0.108174  1.000000

## Monte Carlo (Trade Bootstrap + QuantStats)
- p5_return: -0.006183166134373856
- p25_return: 0.0037305283217926033
- p50_return: 0.011133707893460687
- p75_return: 0.018421671336873613
- p95_return: 0.03019982883310242
- p50_terminal_equity: 101113.37078934608
- probability_of_profit: 0.855
- probability_of_ruin: 0.0
- median_max_drawdown: -0.008015671751262277
- p95_max_drawdown: -0.00418975480533882
- qs_bust_probability: 0.0
- qs_goal_probability: 0.0
- qs_mc_sharpe_median: 0.0
- qs_mc_cagr_median: 0.0

## Experiment History (primary)
- experiment_001: total_return=-0.0015339138209118364, sharpe=-5.660700942977719, max_dd=-0.0018715386481514829
- experiment_002: total_return=-0.00011792549516131956, sharpe=-0.004337432657904823, max_dd=-0.007972901250411946
- experiment_003: total_return=0.0002839827089931024, sharpe=0.0589259042824855, max_dd=-0.001914171108172269
- experiment_004: total_return=0.004434009587451104, sharpe=0.5096347138259734, max_dd=-0.005661133593029888
- experiment_005: total_return=0.004434009587451104, sharpe=0.5096347138259734, max_dd=-0.005661133593029888
- experiment_006: total_return=0.0018942635280141396, sharpe=0.2510454992150398, max_dd=-0.004949185686169755
- experiment_007: total_return=0.003733317731850816, sharpe=0.4992592248630535, max_dd=-0.0038011225440391927

## Delta vs Previous Experiment
- avg_trade_duration_bars: old=48.07692307692308 new=48.41095890410959 delta=0.33403582718651137 improved=False
- avg_win_avg_loss: old=0.8736000193741442 new=0.9169965046103709 delta=0.043396485236226634 improved=False
- cagr: old=0.0006606663304737914 new=0.0013009298576627248 delta=0.0006402635271889334 improved=True
- calmar_ratio: old=0.13348990568690716 new=0.34224886006445765 delta=0.2087589543775505 improved=True
- expectancy: old=2.6457156666931994 new=5.107710071212086 delta=2.4619944045188866 improved=True
- max_drawdown: old=-0.004949185686169755 new=-0.0038011225440391927 delta=0.001148063142130562 improved=True
- profit_factor: old=1.1093333579354212 new=1.1969217533861682 delta=0.08758839545074704 improved=True
- sharpe_ratio: old=0.2510454992150398 new=0.4992592248630535 delta=0.2482137256480137 improved=True
- sortino_ratio: old=0.02226049444722349 new=0.03773409685169608 delta=0.015473602404472594 improved=True
- total_return: old=0.0018942635280141396 new=0.003733317731850816 delta=0.0018390542038366764 improved=True
- total_trades: old=143.0 new=219.0 delta=76.0 improved=False
- win_rate: old=0.5594405594405595 new=0.5662100456621004 delta=0.0067694862215409435 improved=True

## Sensitivity + Walk-forward Summary
- Sensitivity heatmaps: output/plots/sensitivity_*.png
- Parameter analysis: docs/research/parameter_analysis.md
- Walk-forward metrics logged in experiment_005 mc_stats

## Risk Assessment
- Edge remains modest and sensitive to regime changes.
- Walk-forward degradation indicates caution before live deployment.
- Slippage/spread assumptions should be stress-tested further.

## Live Trading Recommendations
1. Paper trade with strict risk caps for at least 4–8 weeks.
2. Add production safeguards (max daily loss, kill switch).
3. Expand OOS validation horizon before scaling.