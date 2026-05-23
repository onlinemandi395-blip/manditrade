from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.paths import BASE_DIR


class SchemaValidationService:
    def __init__(self) -> None:
        self.schemas_dir = BASE_DIR / "schemas"
        self.required_keys = {
            "profile": {"schema_version", "client_id", "manufacturer_id", "business_name", "email", "status"},
            "products": {"schema_version", "products"},
            "manufacturers": {"schema_version", "manufacturers"},
            "clients": {"schema_version", "manufacturer_code", "clients"},
            "notifications_queue": {"schema_version", "messages"},
        }
        self.schema_versions = {
            "profile": "1.0",
            "products": "1.0",
            "manufacturers": "1.0",
            "clients": "1.0",
            "notifications_queue": "1.0",
        }
        self._load_schema_files()

    def _load_schema_files(self) -> None:
        if not self.schemas_dir.exists():
            return
        for path in self.schemas_dir.glob("*_schema.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            schema_name = payload["schema_name"]
            self.required_keys[schema_name] = set(payload.get("required_keys", []))
            self.schema_versions[schema_name] = payload.get("schema_version", "1.0")

    def get_schema_version(self, schema_name: str) -> str:
        return self.schema_versions.get(schema_name, "1.0")

    def validate(self, schema_name: str, payload: dict[str, Any]) -> None:
        required = self.required_keys.get(schema_name, set())
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"{schema_name} schema missing required keys: {', '.join(missing)}")
