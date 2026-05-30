from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class LoggingService:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir

    def log_info(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._write_entry(category, message, details)

    def log_error(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._write_entry(category, message, details)

    def _write_entry(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        target = self.logs_dir / f"{category}.log"
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "category": category,
            "message": message,
            "details": details or {},
        }
        with target.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=True) + "\n")

    def read_recent(self, category: str, limit: int = 50) -> list[dict[str, Any]]:
        target = self.logs_dir / f"{category}.log"
        if not target.exists():
            return []
        lines = target.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
