from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.paths import CONFIGS_DIR


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=8)
def load_config(name: str) -> dict[str, Any]:
    return _load_json(CONFIGS_DIR / name)

