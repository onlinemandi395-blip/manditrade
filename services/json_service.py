from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonService:
    def read_json(self, path: Path, default: Any | None = None) -> Any:
        if not path.exists():
            return default if default is not None else {}
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=True)

