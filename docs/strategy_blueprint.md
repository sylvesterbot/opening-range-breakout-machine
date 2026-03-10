# Phase 2 Strategy Blueprint — Opening Range Breakout (ORB)

## 1) Strategy Definition (Config-driven)

### Required config keys
```yaml
market:
  timezone: America/New_York
  session_open: "09:30"
  session_close: "16:00"

orb:
  opening_range_minutes: 5        # e.g. 5/15/30
  breakout_buffer_bps: 2          # breakout confirmation buffer
  volume_filter_enabled: true
  volume_multiplier_min: 1.2
  one_trade_per_day: true

risk:
  risk_per_trade_pct: 0.005       # 0.5% of equity
  stop_method: "or_opposite"      # or_opposite | atr_multiple
  atr_period: 14
  atr_stop_mult: 1.5
  max_holding_minutes: 120
  force_exit_time: "15:55"

execution:
  slippage_bps: 1.0
  commission_per_share: 0.005
  fill_model: next_bar_open
```

No constants should be hardcoded in strategy logic.

---

## 2) Precise formulas

### 2.1 Opening range bounds
Given bars indexed by timestamp `t` in session day `d`, with opening window length `N` minutes:

- Opening range high:
\[
ORH_d = \max_{t \in [open_d, open_d + N)} High_t
\]

- Opening range low:
\[
ORL_d = \min_{t \in [open_d, open_d + N)} Low_t
\]

### 2.2 Breakout thresholds (buffered)
With buffer in basis points `b`:
\[
U_d = ORH_d \cdot (1 + b/10000)
\]
\[
L_d = ORL_d \cdot (1 - b/10000)
\]

### 2.3 Entry conditions
At bar `t > open_d + N`:

- Long entry if:
\[
Close_t > U_d
\]
(and optional volume filter)

- Short entry if:
\[
Close_t < L_d
\]
(and optional volume filter)

Volume filter example:
\[
Volume_t \ge m \cdot \text{MedianVolume}_{k\text{-bar lookback}}
\]
where `m = volume_multiplier_min`.

### 2.4 Position sizing
Let equity be `E_t`, risk fraction `r`, entry price `P_e`, stop price `P_s`.

Dollar risk budget:
\[
R_\$ = E_t \cdot r
\]

Per-unit risk:
\[
R_{unit} = |P_e - P_s|
\]

Units (shares/contracts, floored):
\[
Q = \left\lfloor \frac{R_\$}{R_{unit}} \right\rfloor
\]

### 2.5 Exit logic
- Stop exit when price crosses stop level.
- Time exit when holding time exceeds `max_holding_minutes`.
- Hard end-of-day exit at `force_exit_time`.

### 2.6 PnL model
For long:
\[
PnL = Q \cdot (P_x - P_e) - Costs
\]
For short:
\[
PnL = Q \cdot (P_e - P_x) - Costs
\]

Transaction costs:
\[
Costs = Q \cdot (commission\_per\_share + slippage\_component)
\]

---

## 3) Backtest pseudocode

```text
for each trading day d:
  bars_d = session bars for d
  if insufficient bars: continue

  compute ORH_d, ORL_d from first N minutes
  compute U_d, L_d (buffered thresholds)

  position = flat
  traded_today = false

  for each bar t after opening window:
    if position is flat:
      if one_trade_per_day and traded_today: break

      if long_condition(t):
        entry = next_bar_open(t)
        stop = determine_stop_long(ORL_d, ATR, config)
        qty = position_size(equity, entry, stop, risk_pct)
        if qty > 0:
          open long position
          traded_today = true

      else if short_condition(t):
        entry = next_bar_open(t)
        stop = determine_stop_short(ORH_d, ATR, config)
        qty = position_size(equity, entry, stop, risk_pct)
        if qty > 0:
          open short position
          traded_today = true

    else:
      if stop_hit(position, t):
        exit at modeled fill
      else if time_exit_reached(position, t):
        exit at modeled fill
      else if t >= force_exit_time:
        exit at modeled fill

  append trade(s) to ledger

compute equity curve from ledger
compute metrics (CAGR, Sharpe, max DD, win rate, profit factor)
```

---

## 4) Acceptance criteria checklist (Phase 2)

- [x] ORB logic defined with explicit formulas
- [x] Entry/exit and sizing rules fully specified
- [x] Pseudocode suitable for direct implementation
- [x] Config-first parameterization documented
- [x] No Strategy implementation code written yet
