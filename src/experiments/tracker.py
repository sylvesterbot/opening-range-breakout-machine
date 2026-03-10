"""Experiment tracking utilities for append-only JSONL logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass
class ExperimentRecord:
    """Represents one experiment entry."""

    experiment_id: str
    timestamp: str
    config_hash: str
    config_snapshot: dict[str, Any]
    metrics: dict[str, float]
    mc_stats: dict[str, float]
    data_range: dict[str, Any]
    notes: str
    status: str


class ExperimentTracker:
    """Append-only JSONL experiment tracker."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def config_hash(config_snapshot: dict[str, Any]) -> str:
        """Compute stable SHA256 hash for config snapshot."""
        payload = json.dumps(config_snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def next_experiment_id(self) -> str:
        """Generate next primary experiment id as experiment_XXX.

        Note: the experiment log may include auxiliary ids (e.g. sensitivity_*) which do not
        participate in the primary experiment sequence.
        """
        existing = self.load_all()
        primary = [r for r in existing if str(r.get("experiment_id", "")).startswith("experiment_")]
        return f"experiment_{len(primary) + 1:03d}"

    def append(
        self,
        config_snapshot: dict[str, Any],
        metrics: dict[str, float],
        mc_stats: dict[str, float],
        data_range: dict[str, Any],
        notes: str,
        status: str,
        experiment_id: str | None = None,
    ) -> ExperimentRecord:
        """Append one experiment record to JSONL and return it."""
        record = ExperimentRecord(
            experiment_id=experiment_id or self.next_experiment_id(),
            timestamp=datetime.now(UTC).isoformat(),
            config_hash=self.config_hash(config_snapshot),
            config_snapshot=config_snapshot,
            metrics=metrics,
            mc_stats=mc_stats,
            data_range=data_range,
            notes=notes,
            status=status,
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__) + "\n")
        return record

    def load_all(self) -> list[dict[str, Any]]:
        """Load all experiments from JSONL."""
        if not self.log_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
