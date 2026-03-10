# Opening Range Breakout (ORB) Research Report

## Scope
This phase gathered verifiable references for ORB-style intraday breakout trading and extracted practical parameter ranges for implementation and testing.

## Source Quality Notes
- Direct, ORB-specific peer-reviewed academic evidence is limited in this pass.
- I included verified practitioner research and market-structure references, plus adjacent academic intraday literature.
- Where a claim is not from peer-reviewed ORB literature, it is marked as practitioner evidence.

## Citations (Verifiable)
1. QuantConnect Research — *Opening Range Breakout for Stocks in Play*  
   URL: https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/
2. EasyLanguage Mastery — *Opening Range Breakout Trading Strategy Design & Implementation* (practitioner backtest write-up)  
   URL: https://easylanguagemastery.com/building-strategies/opening-range-breakout-trading-strategy-design-implementation/
3. Toby Crabel — *Day Trading with Short-Term Price Patterns and Opening Range Breakout* (book)  
   URL: https://www.amazon.com/Day-Trading-Short-Term-Patterns-Opening/dp/0934380171
4. Gao, Han, Li, Zhou (2018) — *Intraday Momentum: The First Half-Hour Return Predicts the Last Half-Hour Return* (adjacent intraday opening-session evidence)  
   DOI: https://doi.org/10.1016/j.jfineco.2018.04.008
5. NYSE Trading Hours (session definition reference for equities open/close)  
   URL: https://www.nyse.com/markets/hours-calendars
6. Alpaca Market Data API docs (intraday 1-min equities data coverage reference)  
   URL: https://docs.alpaca.markets/docs/market-data-api
7. yfinance project (fallback data limitations/usage for prototyping)  
   URL: https://github.com/ranaroussi/yfinance
8. Dukascopy historical data feed (forex primary free source)  
   URL: https://www.dukascopy.com/swiss/english/marketwatch/historical/
9. HistData free forex historical data (fallback source)  
   URL: https://www.histdata.com/

## Extracted ORB Parameter Ranges (with attribution)

### Opening range window
- **5 min / 15 min / 30 min** are the primary windows to test (QuantConnect practitioner research; Crabel ORB framing).

### Breakout confirmation
- Confirmation options to test:
  - close above OR high / below OR low
  - volume spike threshold around **1.5x average intraday bar volume** (QuantConnect-style signal filters and practitioner conventions).

### Stop-loss model
- Baseline: stop at opposite side of opening range (classic ORB convention from Crabel-style rule sets and practitioner implementations).
- Alternative: ATR-based stop for sensitivity testing.

### Take-profit model
- Grid: **1.0R, 1.5R, 2.0R, 3.0R** (common practitioner optimization range; included in prompt and validated as practical for grid testing).

### Session filters
- Trade in the first **2 hours after session open** for baseline ORB (practitioner evidence + opening-session volatility concentration in intraday literature).

### Asset-class adaptation
- Equities: NYSE/NASDAQ regular session anchored at **09:30 ET** (NYSE hours).
- Forex: configurable London/New York session anchor for OR calculation.

## Evidence Summary Table

| Source | Type | ORB/Intraday Finding Used | Reliability Note |
|---|---|---|---|
| QuantConnect ORB research | Practitioner quantitative backtest | Supports ORB implementation structure and stock-selection/filter conventions | Reproducible code-oriented source |
| EasyLanguage Mastery ORB article | Practitioner backtest | Parameter experimentation around OR windows and trade management | Not peer-reviewed; practical only |
| Crabel book | Book / historical practitioner reference | Canonical ORB framing and breakout-style day trading logic | Foundational but older |
| Gao et al. (2018) JFE | Peer-reviewed academic | Opening-period return information relevance for intraday continuation/reversal modeling | Adjacent evidence, not ORB-specific |
| NYSE hours | Exchange reference | Session open/close definitions for US equities | Authoritative market-structure source |

## Defaults Proposed for Phase 2/3 (Research-backed)
- OR window default: **15 min** (test 5/15/30)
- Entry confirmation default: **close breakout**; optional volume filter at **>=1.5x**
- Stop default: **opposite OR boundary**
- Target default: **1.5R** (grid test 1.0/1.5/2.0/3.0)
- Entry window default: **first 2 hours**
- Risk default: **1% equity per trade** (to be validated in sensitivity phase)

## Research Gaps / Caveats
- No single universally accepted ORB peer-reviewed standard with fixed parameters was identified; implementation will treat parameters as hypotheses and validate via backtest + Monte Carlo + sensitivity analysis.
- Academic evidence used here is partly adjacent intraday structure evidence rather than strict ORB-only studies.
