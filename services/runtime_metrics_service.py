from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RuntimeMetricsService:
    def __init__(self, metrics_root: Path) -> None:
        self.metrics_root = metrics_root

    def _daily_path(self, day: str | None = None) -> Path:
        key = day or datetime.now(UTC).strftime("%Y-%m-%d")
        return self.metrics_root / f"{key}.json"

    def increment(self, metric_name: str, amount: int = 1, extra: dict[str, Any] | None = None) -> None:
        path = self._daily_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"date": path.stem, "counters": {}, "samples": []}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"date": path.stem, "counters": {}, "samples": []}
        payload.setdefault("counters", {})
        payload["counters"][metric_name] = int(payload["counters"].get(metric_name, 0)) + amount
        if extra:
            payload.setdefault("samples", []).append(
                {"metric_name": metric_name, "timestamp": datetime.now(UTC).isoformat(), "extra": extra}
            )
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def latest(self) -> dict[str, Any]:
        path = self._daily_path()
        if not path.exists():
            return {"date": path.stem, "counters": {}, "samples": []}
        return json.loads(path.read_text(encoding="utf-8"))
