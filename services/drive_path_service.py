from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DrivePathService:
    ROOT_FOLDER_NAME = "MANDITRADE_DB"
    FOLDER_TREE = {
        "config": "00_config",
        "identity": "01_identity",
        "catalog": "02_catalog",
        "inventory": "03_inventory",
        "carts": "04_carts",
        "orders": "05_orders",
        "logistics": "06_logistics",
        "finance": "07_finance",
        "jobs": "08_jobs",
        "notifications": "09_notifications",
        "actions": "10_actions",
        "intelligence": "11_intelligence",
        "analytics": "12_analytics",
        "audit": "13_audit",
        "runtime": "14_runtime",
        "media": "15_media",
    }
    CONFIG_FILES = {
        "system_config.json",
        "role_permissions.json",
        "navigation_config.json",
        "notification_rules.json",
        "pricing_rules.json",
        "commission_rules.json",
        "category_master.json",
        "state_city_master.json",
        "id_counters.json",
    }

    def __init__(
        self,
        *,
        db_root: Path,
        runtime_root: Path,
        governance_root: Path,
        manufacturers_root: Path,
        public_buyers_root: Path,
        storage_mode: str = "compatibility",
        allow_legacy_fallback: bool = True,
    ) -> None:
        self.db_root = db_root
        self.runtime_root = runtime_root
        self.governance_root = governance_root
        self.manufacturers_root = manufacturers_root
        self.public_buyers_root = public_buyers_root
        self.storage_mode = str(storage_mode or "compatibility").strip().lower()
        self.allow_legacy_fallback = bool(allow_legacy_fallback)

    def ensure_root(self) -> Path:
        self.db_root.mkdir(parents=True, exist_ok=True)
        return self.db_root

    def ensure_canonical_structure(self) -> Path:
        root = self.ensure_root()
        for folder in self.canonical_relative_folders():
            (root / folder).mkdir(parents=True, exist_ok=True)
        return root

    def canonical_relative_folders(self) -> list[Path]:
        folders = [Path(folder) for folder in self.FOLDER_TREE.values()]
        folders.extend(
            [
                Path(self._folder("finance")) / "transactions",
                Path(self._folder("finance")) / "payments",
                Path(self._folder("finance")) / "invoices",
                Path(self._folder("finance")) / "ledgers",
                Path(self._folder("finance")) / "commissions",
                Path(self._folder("finance")) / "disputes",
                Path(self._folder("notifications")) / "in_app",
                Path(self._folder("notifications")) / "email_queue",
                Path(self._folder("notifications")) / "email_history",
                Path(self._folder("notifications")) / "dead_letter",
                Path(self._folder("analytics")) / "snapshots",
                Path(self._folder("media")) / "products",
                Path(self._folder("media")) / "raw_materials",
                Path(self._folder("media")) / "payment_proofs",
                Path(self._folder("media")) / "delivery_proofs",
                Path(self._folder("media")) / "job_images",
                Path(self._folder("media")) / "profile_images",
            ]
        )
        return folders

    def current_year_month(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    def get_registry_path(self, entity: str) -> Path:
        mapping = {
            "users_index": self.db_root / self._folder("identity") / "users_index.json",
            "platform_admins": self.db_root / self._folder("identity") / "platform_admins.json",
            "manufacturers": self.db_root / self._folder("identity") / "manufacturers.json",
            "mahajans": self.db_root / self._folder("identity") / "mahajans.json",
            "public_buyers": self.db_root / self._folder("identity") / "public_buyers.json",
            "workers": self.db_root / self._folder("identity") / "workers.json",
        }
        target = mapping[entity]
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_catalog_path(self, entity: str) -> Path:
        mapping = {
            "products": self.db_root / self._folder("catalog") / "products.json",
            "product_approvals": self.db_root / self._folder("catalog") / "product_approvals.json",
            "raw_materials": self.db_root / self._folder("catalog") / "raw_materials.json",
            "suta_items": self.db_root / self._folder("catalog") / "suta_items.json",
            "packaging_services": self.db_root / self._folder("catalog") / "packaging_services.json",
            "courier_services": self.db_root / self._folder("catalog") / "courier_services.json",
            "categories": self.db_root / self._folder("catalog") / "category_master.json",
            "image_refs": self.db_root / self._folder("catalog") / "image_refs.json",
        }
        target = mapping[entity]
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_order_path(self, order_type: str, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        normalized = str(order_type or "").strip().lower()
        filename_map = {
            "marketplace": "marketplace_orders.json",
            "mandiplace": "mandiplace_orders.json",
            "suta_mandi": "suta_mandi_orders.json",
            "supply": "supply_orders.json",
        }
        target = self.db_root / self._folder("orders") / normalized / month / filename_map.get(normalized, f"{normalized}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_notification_path(self, channel: str, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        normalized = str(channel or "").strip().lower()
        if normalized == "email_queue":
            target = self.db_root / self._folder("notifications") / "email_queue" / "gmail_queue.json"
        elif normalized == "dead_letter":
            target = self.db_root / self._folder("notifications") / "dead_letter" / "failed_notifications.json"
        elif normalized == "email_history":
            target = self.db_root / self._folder("notifications") / "email_history" / month / "sent_emails.json"
        else:
            target = self.db_root / self._folder("notifications") / "in_app" / month / "notifications.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_audit_path(self, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        target = self.db_root / self._folder("audit") / month / "audit_logs.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_media_folder(self, entity_type: str) -> Path:
        normalized = str(entity_type or "").strip().lower()
        mapping = {
            "product": "products",
            "raw_material": "raw_materials",
            "payment_proof": "payment_proofs",
            "delivery_proof": "delivery_proofs",
            "job_image": "job_images",
            "profile_image": "profile_images",
        }
        target = self.db_root / self._folder("media") / mapping.get(normalized, normalized or "misc")
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_runtime_path(self, area: str) -> Path:
        target = self.db_root / self._folder("runtime") / area
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_config_path(self, name: str) -> Path:
        target = self.db_root / self._folder("config") / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_finance_path(self, area: str, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        normalized = str(area or "").strip().lower()
        month_partitioned = {"transactions", "payments", "invoices"}
        target = self.db_root / self._folder("finance") / normalized
        if normalized in month_partitioned:
            target = target / month / f"{normalized}.json"
        elif normalized == "disputes":
            target = target / "disputes.json"
        else:
            target = target / f"{normalized}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_intelligence_path(self, name: str) -> Path:
        target = self.db_root / self._folder("intelligence") / f"{name}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_jobs_path(self, name: str) -> Path:
        target = self.db_root / self._folder("jobs") / f"{name}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_analytics_path(self, name: str, year_month: str | None = None) -> Path:
        normalized = str(name or "").strip().lower()
        if normalized == "snapshots":
            month = year_month or self.current_year_month()
            target = self.db_root / self._folder("analytics") / "snapshots" / month / "snapshots.json"
        else:
            target = self.db_root / self._folder("analytics") / f"{normalized}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def path(self, logical_path: str, *, year_month: str | None = None) -> Path:
        normalized = str(logical_path or "").strip().lower()
        if normalized.startswith("inventory."):
            return self.get_inventory_path(normalized.split(".", 1)[1])
        if normalized == "orders.marketplace":
            return self.get_order_path("marketplace", year_month)
        if normalized == "orders.mandiplace":
            return self.get_order_path("mandiplace", year_month)
        if normalized == "orders.suta_mandi":
            return self.get_order_path("suta_mandi", year_month)
        if normalized == "orders.supply":
            return self.get_order_path("supply", year_month)
        if normalized.startswith("notifications."):
            return self.get_notification_path(normalized.split(".", 1)[1], year_month)
        if normalized.startswith("finance."):
            return self.get_finance_path(normalized.split(".", 1)[1], year_month)
        if normalized.startswith("analytics."):
            return self.get_analytics_path(normalized.split(".", 1)[1], year_month)
        if normalized.startswith("catalog."):
            return self.get_catalog_path(normalized.split(".", 1)[1])
        if normalized.startswith("identity."):
            return self.get_registry_path(normalized.split(".", 1)[1])
        raise ValueError(f"Unsupported logical path: {logical_path}")

    def get_inventory_path(self, name: str) -> Path:
        normalized = str(name or "").strip().lower()
        mapping = {
            "manufacturer_inventory": self.db_root / self._folder("inventory") / "manufacturer_inventory.json",
            "mandiplace_inventory": self.db_root / self._folder("inventory") / "mandiplace_inventory.json",
            "raw_material_inventory": self.db_root / self._folder("inventory") / "raw_material_inventory.json",
            "suta_inventory": self.db_root / self._folder("inventory") / "suta_inventory.json",
            "movements": self.db_root / self._folder("inventory") / "inventory_movements.json",
        }
        target = mapping[normalized]
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def bootstrap_file_definitions(self) -> dict[Path, dict[str, Any]]:
        records_envelope = lambda key="records": {"schema_version": 1, key: [], "updated_at": ""}
        settings_envelope = {"schema_version": 1, "settings": {}}
        config_root = self.db_root / self._folder("config")
        identity_root = self.db_root / self._folder("identity")
        catalog_root = self.db_root / self._folder("catalog")
        inventory_root = self.db_root / self._folder("inventory")
        carts_root = self.db_root / self._folder("carts")
        finance_root = self.db_root / self._folder("finance")
        jobs_root = self.db_root / self._folder("jobs")
        intelligence_root = self.db_root / self._folder("intelligence")
        return {
            config_root / "system_config.json": settings_envelope,
            config_root / "role_permissions.json": settings_envelope,
            config_root / "navigation_config.json": settings_envelope,
            config_root / "notification_rules.json": settings_envelope,
            config_root / "pricing_rules.json": settings_envelope,
            config_root / "commission_rules.json": settings_envelope,
            config_root / "category_master.json": records_envelope("categories"),
            config_root / "state_city_master.json": records_envelope("locations"),
            config_root / "id_counters.json": {"schema_version": 1, "settings": {}, "updated_at": ""},
            identity_root / "users_index.json": records_envelope("users"),
            identity_root / "platform_admins.json": records_envelope("platform_admins"),
            identity_root / "manufacturers.json": records_envelope("manufacturers"),
            identity_root / "mahajans.json": records_envelope("mahajans"),
            identity_root / "public_buyers.json": records_envelope("buyers"),
            identity_root / "workers.json": records_envelope("workers"),
            catalog_root / "products.json": records_envelope("products"),
            catalog_root / "product_approvals.json": records_envelope("product_approvals"),
            catalog_root / "raw_materials.json": records_envelope("raw_materials"),
            catalog_root / "suta_items.json": records_envelope("suta_items"),
            catalog_root / "packaging_services.json": records_envelope("services"),
            catalog_root / "courier_services.json": records_envelope("services"),
            catalog_root / "image_refs.json": records_envelope("records"),
            inventory_root / "manufacturer_inventory.json": records_envelope("items"),
            inventory_root / "mandiplace_inventory.json": records_envelope("items"),
            inventory_root / "raw_material_inventory.json": records_envelope("items"),
            inventory_root / "suta_inventory.json": records_envelope("items"),
            carts_root / "marketplace_carts.json": records_envelope("carts"),
            carts_root / "mandiplace_carts.json": records_envelope("carts"),
            carts_root / "suta_carts.json": records_envelope("carts"),
            carts_root / "supply_carts.json": records_envelope("carts"),
            finance_root / "ledgers" / "mandi_ledgers.json": records_envelope("entries"),
            finance_root / "ledgers" / "supply_ledgers.json": records_envelope("entries"),
            finance_root / "ledgers" / "commission_ledgers.json": records_envelope("entries"),
            finance_root / "commissions" / "marketplace_commissions.json": records_envelope("entries"),
            finance_root / "commissions" / "mandiplace_commissions.json": records_envelope("entries"),
            finance_root / "commissions" / "supply_commissions.json": records_envelope("entries"),
            finance_root / "commissions" / "commission_summary.json": records_envelope("records"),
            finance_root / "disputes" / "disputes.json": records_envelope("disputes"),
            jobs_root / "jobs.json": records_envelope("jobs"),
            jobs_root / "applications.json": records_envelope("applications"),
            jobs_root / "assignments.json": records_envelope("assignments"),
            self.db_root / self._folder("notifications") / "email_queue" / "gmail_queue.json": records_envelope("emails"),
            self.db_root / self._folder("notifications") / "dead_letter" / "failed_notifications.json": records_envelope("failures"),
            self.db_root / self._folder("runtime") / "drive_smoke_test.json": records_envelope("records"),
            intelligence_root / "alerts.json": records_envelope("alerts"),
            intelligence_root / "recommendations.json": records_envelope("recommendations"),
            intelligence_root / "kpis.json": records_envelope("kpis"),
            intelligence_root / "health_scores.json": records_envelope("scores"),
            intelligence_root / "search_index.json": records_envelope("records"),
        }

    def is_canonical_mode(self) -> bool:
        return self.storage_mode == "canonical"

    def set_storage_mode(self, mode: str) -> None:
        normalized = str(mode or "compatibility").strip().lower()
        if normalized not in {"compatibility", "canonical"}:
            raise ValueError("Unsupported storage mode.")
        self.storage_mode = normalized

    def resolve_preferred_path(self, *, canonical: Path, legacy: Path | None = None, legacy_allowed: bool | None = None) -> Path:
        allow_legacy = self.allow_legacy_fallback if legacy_allowed is None else bool(legacy_allowed)
        if self.is_canonical_mode():
            if canonical.exists() or not (allow_legacy and legacy and legacy.exists()):
                return canonical
            return legacy
        if allow_legacy and legacy and legacy.exists():
            return legacy
        return canonical

    def _folder(self, logical_name: str) -> str:
        return self.FOLDER_TREE[logical_name]
