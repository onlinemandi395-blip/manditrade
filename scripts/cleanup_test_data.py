from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.paths import APP_RUNTIME_DIR, BASE_DIR


PREFIXES = ("PILOT_TEST_", "TEST_", "DEMO_")
SCAN_ROOTS = (BASE_DIR / "data", BASE_DIR / "runtime")
RECORD_KEYS = {
    "manufacturer_code",
    "manufacturer_id",
    "mahajan_id",
    "product_id",
    "raw_material_id",
    "order_id",
    "public_order_id",
    "mandi_order_id",
    "entry_id",
    "ledger_id",
    "alert_id",
    "job_id",
    "worker_id",
    "notification_id",
    "business_name",
    "email",
    "linked_email",
}


def _matches_prefix(value: str) -> bool:
    normalized = value.strip().upper()
    return any(normalized.startswith(prefix) for prefix in PREFIXES)


def _record_matches(record: dict[str, Any]) -> bool:
    for key, value in record.items():
        if key not in RECORD_KEYS:
            continue
        if isinstance(value, str) and _matches_prefix(value):
            return True
    return False


def _archive_path(relative_path: Path, timestamp: str) -> Path:
    return APP_RUNTIME_DIR / "release_cleanup" / timestamp / relative_path


def _scrub_lists(node: Any, removed: list[dict[str, Any]], file_path: Path) -> tuple[Any, bool]:
    changed = False
    if isinstance(node, list):
        cleaned: list[Any] = []
        for item in node:
            if isinstance(item, dict) and _record_matches(item):
                removed.append({"path": str(file_path), "action": "remove_record", "keys": sorted(item.keys())[:8]})
                changed = True
                continue
            updated, item_changed = _scrub_lists(item, removed, file_path)
            changed = changed or item_changed
            cleaned.append(updated)
        return cleaned, changed
    if isinstance(node, dict):
        cleaned_dict: dict[str, Any] = {}
        for key, value in node.items():
            updated, item_changed = _scrub_lists(value, removed, file_path)
            cleaned_dict[key] = updated
            changed = changed or item_changed
        return cleaned_dict, changed
    return node, False


def _process_json(path: Path) -> tuple[str, Any]:
    if _matches_prefix(path.stem):
        return "archive_file", None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "skip_invalid_json", None
    if isinstance(payload, dict) and _record_matches(payload):
        return "archive_file", payload
    removed: list[dict[str, Any]] = []
    updated, changed = _scrub_lists(payload, removed, path)
    if changed:
        return "rewrite_file", {"payload": updated, "removed": removed}
    return "keep", None


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive or remove seeded test/demo records without touching real data.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without editing files.")
    parser.add_argument("--execute", action="store_true", help="Apply cleanup changes and archive original files.")
    args = parser.parse_args()
    execute = bool(args.execute)
    if not args.dry_run and not args.execute:
        args.dry_run = True

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary = {"mode": "execute" if execute else "dry-run", "files_rewritten": 0, "files_archived": 0, "records_removed": 0, "skipped_invalid_json": 0}

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            if "release_reports" in path.parts or "release_snapshots" in path.parts:
                continue
            action, payload = _process_json(path)
            if action == "keep":
                continue
            if action == "skip_invalid_json":
                summary["skipped_invalid_json"] += 1
                continue
            relative = path.relative_to(BASE_DIR)
            archive_target = _archive_path(relative, timestamp)
            if action == "archive_file":
                summary["files_archived"] += 1
                print(f"[ARCHIVE] {relative}")
                if execute:
                    archive_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), str(archive_target))
                continue
            if action == "rewrite_file":
                removed = payload["removed"]
                summary["files_rewritten"] += 1
                summary["records_removed"] += len(removed)
                print(f"[REWRITE] {relative} ({len(removed)} records)")
                if execute:
                    archive_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, archive_target)
                    path.write_text(json.dumps(payload["payload"], indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
