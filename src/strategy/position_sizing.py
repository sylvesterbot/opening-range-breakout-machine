"""Position sizing models for ORB strategy."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def compute_position_size(
    account_equity: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_price: float,
    max_position_pct: float,
) -> float:
    """Compute fixed-fractional position size with cap and safety guards.

    Args:
        account_equity: Current account equity in currency units.
        risk_per_trade_pct: Percent of equity risked per trade.
        entry_price: Planned entry price.
        stop_price: Stop-loss price.
        max_position_pct: Max position notional as percent of equity.

    Returns:
        Position size in units/shares. Returns 0.0 for invalid/unsafe inputs.
    """
    unit_risk = abs(entry_price - stop_price)
    if account_equity <= 0 or entry_price <= 0 or unit_risk <= 0:
        logger.warning(
            "Rejected position size due to invalid inputs: equity=%s entry=%s stop=%s",
            account_equity,
            entry_price,
            stop_price,
        )
        return 0.0

    dollar_risk = account_equity * (risk_per_trade_pct / 100.0)
    raw_size = dollar_risk / unit_risk
    cap_size = (account_equity * (max_position_pct / 100.0)) / entry_price
    size = min(raw_size, cap_size)
    return float(max(size, 0.0))
