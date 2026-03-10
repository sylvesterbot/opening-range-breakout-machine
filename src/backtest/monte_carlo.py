"""Trade-level bootstrap Monte Carlo simulation."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation."""

    iterations: int
    max_iterations: int
    convergence_threshold: float
    early_stopping: bool
    slippage_range: tuple[float, float]
    random_seed: int
    initial_capital: float


@dataclass
class MonteCarloResult:
    """Container for Monte Carlo outputs."""

    iterations_completed: int
    terminal_equities: np.ndarray
    max_drawdowns: np.ndarray
    sharpes: np.ndarray
    equity_curves: list[np.ndarray]
    running_mean: np.ndarray
    stats: dict[str, float]


def run_trade_bootstrap_monte_carlo(trades: pd.DataFrame, config: MonteCarloConfig) -> MonteCarloResult:
    """Run trade-level bootstrap MC with slippage perturbation and convergence checks."""
    if trades.empty or "net_pnl" not in trades.columns:
        empty = np.array([], dtype=float)
        return MonteCarloResult(0, empty, empty, empty, [], empty, {
            "p5_return": 0.0,
            "p25_return": 0.0,
            "p50_return": 0.0,
            "p75_return": 0.0,
            "p95_return": 0.0,
            "p50_terminal_equity": 0.0,
            "probability_of_profit": 0.0,
            "probability_of_ruin": 0.0,
            "median_max_drawdown": 0.0,
            "p95_max_drawdown": 0.0,
        })

    rng = np.random.default_rng(config.random_seed)
    pnl = trades["net_pnl"].to_numpy(dtype=float)
    n = len(pnl)

    terminals: list[float] = []
    mdds: list[float] = []
    sharpes: list[float] = []
    curves: list[np.ndarray] = []
    running_mean: list[float] = []

    max_iters = min(config.max_iterations, max(config.iterations, 1000))
    for i in range(max_iters):
        sample = rng.choice(pnl, size=n, replace=True)
        slip = rng.uniform(config.slippage_range[0], config.slippage_range[1], size=n)
        sample_adj = sample * (1.0 - slip)
        eq = config.initial_capital + np.cumsum(sample_adj)
        eq = np.insert(eq, 0, config.initial_capital)

        terminal = float(eq[-1])
        roll_max = np.maximum.accumulate(eq)
        dd = (eq / np.maximum(roll_max, 1e-9)) - 1.0
        mdd = float(dd.min())

        rets = np.diff(eq) / np.maximum(eq[:-1], 1e-9)
        sharpe = float((rets.mean() / rets.std()) * np.sqrt(252)) if rets.std() > 0 else 0.0

        terminals.append(terminal)
        mdds.append(mdd)
        sharpes.append(sharpe)
        curves.append(eq)

        mean_t = float(np.mean(terminals))
        running_mean.append(mean_t)

        if config.early_stopping and (i + 1) % 500 == 0 and i >= 999:
            prev = running_mean[i - 499]
            if abs(mean_t - prev) / max(abs(prev), 1e-9) < config.convergence_threshold:
                break

    t = np.array(terminals)
    ret = (t / config.initial_capital) - 1.0
    mdd_a = np.array(mdds)
    stats = {
        "p5_return": float(np.percentile(ret, 5)),
        "p25_return": float(np.percentile(ret, 25)),
        "p50_return": float(np.percentile(ret, 50)),
        "p75_return": float(np.percentile(ret, 75)),
        "p95_return": float(np.percentile(ret, 95)),
        "p50_terminal_equity": float(np.percentile(t, 50)),
        "probability_of_profit": float(np.mean(t > config.initial_capital)),
        "probability_of_ruin": float(np.mean(t < (0.5 * config.initial_capital))),
        "median_max_drawdown": float(np.median(mdd_a)),
        "p95_max_drawdown": float(np.percentile(mdd_a, 95)),
    }

    return MonteCarloResult(
        iterations_completed=len(terminals),
        terminal_equities=t,
        max_drawdowns=mdd_a,
        sharpes=np.array(sharpes),
        equity_curves=curves,
        running_mean=np.array(running_mean),
        stats=stats,
    )
