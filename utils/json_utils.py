from __future__ import annotations

import json


def to_json(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)
