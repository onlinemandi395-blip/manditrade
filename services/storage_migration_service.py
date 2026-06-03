from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StorageMigrationService:
    def __init__(
        self,
        *,
        drive_path_service,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        governance_root: Path,
        public_buyers_root: Path,
        public_orders_root: Path,
        public_payments_root: Path,
        runtime_root: Path,
    ) -> None:
        self.drive_path_service = drive_path_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.governance_root = governance_root
        self.public_buyers_root = public_buyers_root
        self.public_orders_root = public_orders_root
        self.public_payments_root = public_payments_root
        self.runtime_root = runtime_root

    def run(
        self,
        *,
        mode: str,
        rehearsal: bool = False,
        report_dir: Path | None = None,
    ) -> dict[str, Any]:
        migration_id = self.id_allocator_service.allocate("event")
        started_at = datetime.now(UTC).isoformat()
        source_files = self._discover_legacy_sources()
        canonical_documents, report_state = self._build_canonical_documents(source_files)
        records_migrated = sum(item["count"] for item in canonical_documents.values())
        if mode == "execute":
            self.drive_path_service.ensure_canonical_structure()
            for target, doc in canonical_documents.items():
                self.safe_drive_write_service.replace_document(Path(target), doc)
        completed_at = datetime.now(UTC).isoformat()
        report = {
            "migration_id": migration_id,
            "mode": mode,
            "rehearsal": rehearsal,
            "started_at": started_at,
            "completed_at": completed_at,
            "source_files_scanned": len(source_files),
            "records_discovered": report_state["records_discovered"],
            "records_migrated": records_migrated if mode == "execute" else 0,
            "records_skipped": report_state["records_skipped"],
            "conflicts": report_state["conflicts"],
            "errors": report_state["errors"],
            "canonical_counts": {target: payload["count"] for target, payload in canonical_documents.items()},
            "legacy_counts": report_state["legacy_counts"],
            "checksum_summary": {target: payload["checksum"] for target, payload in canonical_documents.items()},
            "recommendation": "FAIL" if report_state["errors"] else "REVIEW" if report_state["conflicts"] else "PASS",
        }
        self._write_report(report, report_dir=report_dir, rehearsal=rehearsal)
        return report

    def _discover_legacy_sources(self) -> list[Path]:
        candidates: list[Path] = []
        candidates.extend(sorted(self.governance_root.glob("*.json")))
        if self.public_buyers_root.exists():
            candidates.extend(sorted(self.public_buyers_root.glob("*.json")))
            candidates.extend(sorted(self.public_buyers_root.glob("*/*.json")))
        if self.public_orders_root.exists():
            candidates.extend(sorted(self.public_orders_root.glob("*/*.json")))
        if self.public_payments_root.exists():
            candidates.extend(sorted(self.public_payments_root.glob("*/*.json")))
        if (self.runtime_root / "carts").exists():
            candidates.extend(sorted((self.runtime_root / "carts").glob("*/*/*.json")))
        for relative in [
            self.runtime_root / "alerts" / "alerts.json",
            self.runtime_root / "recommendations" / "latest.json",
            self.runtime_root / "kpis" / "latest.json",
            self.runtime_root / "search_index" / "latest.json",
        ]:
            if relative.exists():
                candidates.append(relative)
        audit_dir = self.runtime_root / "audit" / "audit_logs"
        if audit_dir.exists():
            candidates.extend(sorted(audit_dir.glob("*.json")))
        return candidates

    def _build_canonical_documents(self, source_files: list[Path]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        canonical: dict[str, dict[str, Any]] = {}
        seen: dict[str, set[str]] = {}
        state = {
            "records_discovered": 0,
            "records_skipped": 0,
            "conflicts": [],
            "errors": [],
            "legacy_counts": {},
        }
        for source in source_files:
            try:
                payload = self.json_service.read_json(source, {})
            except Exception as exc:  # noqa: BLE001
                state["errors"].append({"source": str(source), "error": str(exc)})
                continue
            mappings = self._map_source(source, payload)
            for target_path, list_key, rows, id_field in mappings:
                state["legacy_counts"][str(source)] = state["legacy_counts"].get(str(source), 0) + len(rows)
                target_key = str(target_path)
                if target_key not in canonical:
                    canonical[target_key] = {"schema_version": "1.0", list_key: [], "count": 0, "checksum": ""}
                    seen[target_key] = set()
                for row in rows:
                    state["records_discovered"] += 1
                    normalized = self._normalize_entity(dict(row), id_field=id_field)
                    record_id = str(normalized.get(id_field) or normalized.get("id") or "").strip()
                    if not record_id:
                        state["records_skipped"] += 1
                        state["conflicts"].append({"source": str(source), "reason": "missing_id", "record": row})
                        continue
                    if record_id in seen[target_key]:
                        state["records_skipped"] += 1
                        continue
                    seen[target_key].add(record_id)
                    canonical[target_key][list_key].append(normalized)
                    canonical[target_key]["count"] += 1
        for target_key, doc in canonical.items():
            for key, value in doc.items():
                if isinstance(value, list):
                    value.sort(key=lambda item: str(item.get("id", "")))
            doc["checksum"] = hashlib.sha256(repr(doc).encode("utf-8")).hexdigest()
        return canonical, state

    def _map_source(self, source: Path, payload: Any) -> list[tuple[Path, str, list[dict[str, Any]], str]]:
        mappings: list[tuple[Path, str, list[dict[str, Any]], str]] = []
        name = source.name
        if name == "manufacturers.json":
            mappings.append((self.drive_path_service.get_registry_path("manufacturers"), "manufacturers", payload.get("manufacturers", []), "manufacturer_code"))
        elif name == "mahajans.json":
            mappings.append((self.drive_path_service.get_registry_path("mahajans"), "mahajans", payload.get("mahajans", []), "mahajan_id"))
        elif name == "products.json":
            mappings.append((self.drive_path_service.get_catalog_path("products"), "products", payload.get("products", []), "product_id"))
        elif name == "raw_materials.json":
            mappings.append((self.drive_path_service.get_catalog_path("raw_materials"), "raw_materials", payload.get("raw_materials", []), "raw_material_id"))
        elif name == "supply_orders.json":
            mappings.append((self.drive_path_service.get_order_path("supply"), "supply_orders", payload.get("supply_orders", []), "mandi_order_id"))
        elif name == "supply_ledgers.json":
            mappings.append((self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["finance"] / "ledgers" / "supply_ledgers.json", "entries", payload.get("entries", []), "entry_id"))
        elif name == "jobs.json":
            mappings.append((self.drive_path_service.get_jobs_path("jobs"), "jobs", payload.get("jobs", []), "job_id"))
            mappings.append((self.drive_path_service.get_jobs_path("applications"), "applications", payload.get("applications", []), "application_id"))
        elif name == "index.json" and source.parent == self.public_buyers_root:
            mappings.append((self.drive_path_service.get_registry_path("public_buyers"), "buyers", payload.get("buyers", []), "public_buyer_id"))
        elif name.endswith(".json") and source.parent.parent == self.public_orders_root:
            month = source.parent.name
            mappings.append((self.drive_path_service.get_order_path("marketplace", month), "marketplace_orders", [payload], "public_order_id"))
        elif name.endswith(".json") and source.parent.parent == self.public_payments_root:
            mappings.append((self.drive_path_service.get_finance_path("payments", self.drive_path_service.current_year_month()), "payments", [payload], "payment_id"))
        elif source.parent.name in {"public_buyer", "manufacturer", "worker", "mahajan"} or source.parent.parent.name == "carts":
            mappings.append((self.drive_path_service.db_root / self.drive_path_service.FOLDER_TREE["carts"] / f"{source.stem}.json", "carts", [payload], "cart_id"))
        elif name == "alerts.json":
            mappings.append((self.drive_path_service.get_intelligence_path("alerts"), "alerts", payload.get("alerts", payload if isinstance(payload, list) else []), "alert_id"))
        elif name == "latest.json" and "recommendations" in source.parts:
            mappings.append((self.drive_path_service.get_intelligence_path("recommendations"), "recommendations", payload.get("recommendations", payload.get("items", [])), "id"))
        elif name == "latest.json" and "kpis" in source.parts:
            mappings.append((self.drive_path_service.get_intelligence_path("kpis"), "kpis", [payload], "id"))
        elif name == "latest.json" and "search_index" in source.parts:
            mappings.append((self.drive_path_service.get_intelligence_path("search_index"), "records", payload.get("records", []), "entity_id"))
        elif "audit_logs" in source.parts:
            try:
                month = source.stem[:7]
            except Exception:
                month = self.drive_path_service.current_year_month()
            mappings.append((self.drive_path_service.get_audit_path(month), "audit_logs", payload.get("events", payload if isinstance(payload, list) else []), "event_id"))
        elif name == "notifications.json":
            month = self.drive_path_service.current_year_month()
            mappings.append((self.drive_path_service.get_notification_path("in_app", month), "notifications", payload.get("notifications", []), "notification_id"))
        return mappings

    def _normalize_entity(self, row: dict[str, Any], *, id_field: str) -> dict[str, Any]:
        identifier = row.get(id_field) or row.get("id") or row.get("notification_id") or row.get("event_id") or ""
        created_at = str(row.get("created_at") or row.get("timestamp") or datetime.now(UTC).isoformat())
        updated_at = str(row.get("updated_at") or created_at)
        created_by = row.get("created_by") or row.get("actor") or row.get("owner_email") or row.get("email") or "system"
        updated_by = row.get("updated_by") or created_by
        normalized = dict(row)
        normalized["id"] = identifier
        normalized[id_field] = identifier
        normalized.setdefault("status", row.get("profile_status") or row.get("payment_status") or "ACTIVE")
        normalized["created_at"] = created_at
        normalized["updated_at"] = updated_at
        normalized["created_by"] = created_by
        normalized["updated_by"] = updated_by
        normalized["version"] = int(row.get("version", 1) or 1)
        return normalized

    def _write_report(self, report: dict[str, Any], *, report_dir: Path | None, rehearsal: bool) -> Path:
        report_dir = report_dir or (self.runtime_root / "migration_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        prefix = "rehearsal_report" if rehearsal else "migration"
        mode = str(report.get("mode") or "dry_run").strip().lower()
        target = report_dir / f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        latest = report_dir / "latest_migration_report.json"
        latest_mode = report_dir / f"latest_{mode}_migration_report.json"
        latest_rehearsal = report_dir / "latest_rehearsal_migration_report.json"
        latest_rehearsal_mode = report_dir / f"latest_rehearsal_{mode}_migration_report.json"
        self.safe_drive_write_service.replace_document(target, report)
        if rehearsal:
            self.safe_drive_write_service.replace_document(latest_rehearsal, report)
            self.safe_drive_write_service.replace_document(latest_rehearsal_mode, report)
        else:
            self.safe_drive_write_service.replace_document(latest, report)
            self.safe_drive_write_service.replace_document(latest_mode, report)
        return target
