from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.drive_path_service import DrivePathService
from utils.paths import BASE_DIR, DATA_DIR


class DriveConfigService:
    CONFIG_FILE_NAMES = (
        "system_config.json",
        "oauth_config.json",
        "feature_flags.json",
        "subscription_plans.json",
        "notification_rules.json",
        "navigation_config.json",
    )

    def __init__(self, *, base_dir: Path | None = None, root_folder_name: str | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR
        self.root_folder_name = str(root_folder_name or DrivePathService.ROOT_FOLDER_NAME).strip() or DrivePathService.ROOT_FOLDER_NAME
        self.legacy_config_dir = self.base_dir / "configs"
        self.canonical_config_dir = DATA_DIR / self.root_folder_name / DrivePathService.FOLDER_TREE["config"]

    def ensure_canonical_config_dir(self) -> Path:
        self.canonical_config_dir.mkdir(parents=True, exist_ok=True)
        return self.canonical_config_dir

    def canonical_config_path(self, name: str) -> Path:
        return self.ensure_canonical_config_dir() / name

    def legacy_config_path(self, name: str) -> Path:
        return self.legacy_config_dir / name

    def resolve_config_path(self, name: str) -> Path:
        canonical = self.canonical_config_path(name)
        if canonical.exists():
            return canonical
        legacy = self.legacy_config_path(name)
        if legacy.exists():
            return legacy
        return canonical

    def load_json(self, name: str) -> dict[str, Any]:
        path = self.resolve_config_path(name)
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def seed_from_legacy(self, *, remove_legacy: bool = False, overwrite: bool = True) -> list[dict[str, str]]:
        self.ensure_canonical_config_dir()
        results: list[dict[str, str]] = []
        for name in self.CONFIG_FILE_NAMES:
            legacy = self.legacy_config_path(name)
            canonical = self.canonical_config_path(name)
            if not legacy.exists():
                results.append({"name": name, "action": "skip_missing_legacy", "path": str(canonical)})
                continue
            if canonical.exists() and not overwrite:
                results.append({"name": name, "action": "keep_existing_canonical", "path": str(canonical)})
                continue
            canonical.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
            results.append({"name": name, "action": "copied_to_canonical", "path": str(canonical)})
            if remove_legacy:
                legacy.unlink(missing_ok=True)
                results.append({"name": name, "action": "removed_legacy", "path": str(legacy)})
        return results
