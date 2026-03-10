"""Equity curve chart generation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(equity_curve: pd.DataFrame, output_path: Path) -> Path:
    """Plot and save equity curve to output path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(pd.to_datetime(equity_curve["timestamp"]), equity_curve["equity"], label="Strategy")
    ax.set_title("ORB Equity Curve")
    ax.set_ylabel("Equity")
    ax.set_xlabel("Time")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
