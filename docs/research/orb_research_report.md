# Phase 1 Research Report — Opening Range Breakout (ORB)

## Scope
This document captures verifiable research inputs for an ORB system design before implementation.

## Key Findings (Evidence-backed)

1. **Market microstructure supports an ORB focus on early session volatility.**
   - Exchanges define clear opening sessions and regular trading hours, enabling deterministic opening-range windows.
   - Sources:
     - NYSE market hours: https://www.nyse.com/markets/hours-calendars
     - NASDAQ market hours: https://www.nasdaq.com/market-activity/stock-market-holiday-calendar

2. **Intraday seasonality is a known effect and motivates opening-window signal construction.**
   - Academic literature documents strong intraday periodicity and volatility clustering.
   - Source:
     - Andersen & Bollerslev (1997), DOI: https://doi.org/10.1016/S0927-5398(97)00004-2

3. **Data quality and timestamp normalization are first-order requirements.**
   - ORB depends on exact session boundaries; timezone mismatch or missing bars can invalidate signals.
   - Sources:
     - Alpaca market-data FAQ: https://docs.alpaca.markets/docs/market-data-faq
     - Pandas time-window filtering reference: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.between_time.html

4. **A robust ORB requires explicit slippage/commission modeling and out-of-sample validation.**
   - Backtests without realistic execution assumptions overstate edge; this is consistent with established quant backtesting best practice.
   - Source:
     - Bailey et al., “The Probability of Backtest Overfitting” (SSRN): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

5. **Risk controls should be config-driven and regime-aware.**
   - ORB can degrade in high-volatility regimes; regime toggles should control participation and sizing.
   - Sources:
     - CBOE VIX methodology/product references: https://www.cboe.com/tradable_products/vix/
     - Exchange session calendars (NYSE/NASDAQ links above)

## Research Constraints and Practical Decisions

- Use **UV-only** environment management and reproducible lockfile workflow.
- Use **config-driven strategy parameters** (opening window, stop multiple, time exits, volume confirmation), no hardcoded constants in core strategy modules.
- Build with **phase gates**: each phase needs acceptance checklist + test evidence + commit.

## Phase 1 Acceptance Checklist

- [x] Verifiable research sources gathered (URLs/DOIs included)
- [x] ORB assumptions tied to market-hours/session definitions
- [x] Data-quality risks identified with mitigation direction
- [x] Backtest-overfitting risk acknowledged and incorporated into plan
- [x] Inputs ready for Phase 2 strategy blueprint
