from __future__ import annotations

from pathlib import Path

from experiments.comparator import compare_experiments
from experiments.tracker import ExperimentTracker


def test_tracker_append_and_load(tmp_path: Path) -> None:
    tracker = ExperimentTracker(tmp_path / "exp.jsonl")
    rec = tracker.append(
        config_snapshot={"a": 1},
        metrics={"total_return": 0.1},
        mc_stats={"p50_return": 0.05},
        data_range={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        notes="baseline",
        status="baseline",
    )
    assert rec.experiment_id == "experiment_001"
    rows = tracker.load_all()
    assert len(rows) == 1

    tracker.append(
        experiment_id="sensitivity_001",
        config_snapshot={"b": 2},
        metrics={"total_return": 0.0},
        mc_stats={},
        data_range={},
        notes="aux",
        status="experimental",
    )
    rec2 = tracker.append(
        config_snapshot={"c": 3},
        metrics={"total_return": 0.2},
        mc_stats={},
        data_range={},
        notes="next",
        status="improvement",
    )
    assert rec2.experiment_id == "experiment_002"


def test_comparator_directionality() -> None:
    old = {"metrics": {"total_return": 0.1, "max_drawdown": -0.2}}
    new = {"metrics": {"total_return": 0.2, "max_drawdown": -0.1}}
    rows = {r["metric"]: r for r in compare_experiments(old, new)}
    assert rows["total_return"]["improved"] is True
    assert rows["max_drawdown"]["improved"] is True
