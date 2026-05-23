from __future__ import annotations

from pathlib import Path
from typing import Any


class BootstrapService:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def ensure_runtime_structure(self) -> None:
        for relative in (
            "runtime/tokens",
            "runtime/backups",
            "runtime/logs",
            "runtime/queue",
            "data/manufacturers",
            "data/governance",
        ):
            (self.base_dir / relative).mkdir(parents=True, exist_ok=True)

    def demo_mode_enabled(self, system_config: dict[str, Any]) -> bool:
        return bool(system_config.get("app", {}).get("demo_mode", False))
