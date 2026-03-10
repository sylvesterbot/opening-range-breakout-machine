# ORB Strategy Blueprint

## 1) Session and Opening Range Definitions

Let trading day be indexed by \(d\), bar timestamp by \(t\), and session open time by \(T_{open,d}\).

- Session profile (configurable):
  - Equity: \(T_{open}=09{:}30\) US/Eastern
  - Forex London: \(08{:}00\) Europe/London
  - Forex New York: \(08{:}00\) US/Eastern
- Opening range length: \(N \in \{5,15,30\}\) minutes
- Opening range interval:
  \[
  \mathcal{I}_{OR,d} = [T_{open,d}, T_{open,d} + N\text{ min})
  \]
- Opening range bounds:
  \[
  ORH_d = \max_{t \in \mathcal{I}_{OR,d}} High_t, \quad ORL_d = \min_{t \in \mathcal{I}_{OR,d}} Low_t
  \]
- Range size:
  \[
  ORR_d = ORH_d - ORL_d
  \]

### Data/Calendar handling rules
- Exclude pre-market from OR for equity profile.
- For half-days/early close, still compute OR from session open; force liquidation \(exit\_before\_close\_minutes\) before early close.
- If bars are missing inside \(\mathcal{I}_{OR,d}\), mark day invalid for trading unless gap tolerance in config permits interpolation.

## 2) Entry Rules

Define entry window end:
\[
T_{entry\_end,d} = T_{open,d} + H\text{ hours}
\]
where \(H\) is configurable (default 2).

For each bar \(t\in[T_{open,d}+N\text{ min}, T_{entry\_end,d}]\):

### Long trigger
\[
Close_t > ORH_d
\]
with confirmation mode:
- `close`: above condition only
- `volume`: \(Volume_t \ge m \cdot \overline{Volume}_{lookback,t}\)
- `both`: both conditions true

### Short trigger
\[
Close_t < ORL_d
\]
with same confirmation modes.

### Trade frequency
- Max entries per direction per day: \(E_{max}\) (default 1).

## 3) Exit Rules

For long entry price \(P_{in}\):
- Stop-loss (default): \(P_{sl} = ORL_d\)
- Risk unit: \(R = P_{in} - P_{sl}\)
- Take-profit: \(P_{tp} = P_{in} + kR\), where \(k\in\{1.0,1.5,2.0,3.0\}\)

For short:
- \(P_{sl} = ORH_d\)
- \(R = P_{sl} - P_{in}\)
- \(P_{tp} = P_{in} - kR\)

### Time-based liquidation
Force close all open positions at:
\[
T_{force\_exit,d} = T_{close,d} - M\text{ minutes}
\]
where \(M\) is configurable.

### Optional trailing stop
Activate trailing when unrealized PnL \(\ge aR\), with \(a\) default 1.0.
Then trailing distance \(= bR\), \(b\) default 0.5.

## 4) Position Sizing

Given account equity \(A_t\), risk fraction \(r\) (default 0.01):
\[
\text{DollarRisk} = A_t \cdot r
\]
\[
\text{UnitRisk} = |P_{in} - P_{sl}|
\]
\[
\text{RawSize} = \frac{\text{DollarRisk}}{\text{UnitRisk}}
\]

Cap by max position fraction \(c\) (default 0.10):
\[
\text{CapSize} = \frac{A_t \cdot c}{P_{in}}
\]
\[
\text{Size} = \max(0, \min(\text{RawSize}, \text{CapSize}))
\]

### Edge-case guards
- If \(\text{UnitRisk} \le 0\): reject signal (avoid division by zero/invalid stop).
- If size < minimum lot/share: reject trade.

## 5) Optional Filters

- Minimum range filter:
\[
ORR_d \ge \alpha \cdot ATR_{daily,d}
\]
- Maximum range filter:
\[
ORR_d \le \beta \cdot ATR_{daily,d}
\]
- Trend filter (long only):
\[
Close^{daily}_d > SMA_{n}^{daily}(d)
\]
- Trend filter (short only):
\[
Close^{daily}_d < SMA_{n}^{daily}(d)
\]

## Signal Generation Pseudocode

```text
for each day d:
  load session bars for day d in target timezone
  if insufficient OR bars: continue

  ORH, ORL = opening_range(day=d, minutes=N)
  if not range_filters_pass(ORH, ORL, atr): continue

  long_used = 0
  short_used = 0

  for bar t from OR end to entry_window_end:
    if long_used < E_max and long_condition(t, ORH, confirmation):
      create long trade with SL=ORL, TP=P_in + k*(P_in-ORL)
      long_used += 1

    if short_used < E_max and short_condition(t, ORL, confirmation):
      create short trade with SL=ORH, TP=P_in - k*(ORH-P_in)
      short_used += 1

    update open trades (stop/tp/trailing)

  force close any open trade at session_close - M minutes
```

## Risk Principles and Edge Framing
- Expectancy objective:
\[
\mathbb{E}[trade] = p_w \cdot AvgWin - (1-p_w) \cdot AvgLoss > 0
\]
- Robustness objective: maintain positive expectancy across neighborhoods of \((N, k, r)\), not just one point estimate.
- No overnight risk: all positions flat by end-of-session profile.
