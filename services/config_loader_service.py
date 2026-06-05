from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigLoaderService:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.config_dir = self.base_dir / "configs"

    def load(self, name: str) -> dict[str, Any]:
        path = self.config_dir / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def load_language(self, code: str) -> dict[str, Any]:
        path = self.config_dir / "languages" / f"{code}.json"
        return json.loads(path.read_text(encoding="utf-8"))
