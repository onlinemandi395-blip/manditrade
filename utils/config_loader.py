from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from services.drive_config_service import DriveConfigService


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=8)
def load_config(name: str) -> dict[str, Any]:
    service = DriveConfigService()
    return _load_json(service.resolve_config_path(name))

