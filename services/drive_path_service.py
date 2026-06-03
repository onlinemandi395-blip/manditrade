from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


class DrivePathService:
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
        for folder in [
            "config",
            "registry",
            "catalog",
            "inventory",
            "orders",
            "carts",
            "payments",
            "ledgers",
            "commissions",
            "jobs",
            "notifications",
            "actions",
            "analytics",
            "audit",
            "runtime",
            "media",
        ]:
            (root / folder).mkdir(parents=True, exist_ok=True)
        return root

    def current_year_month(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    def get_registry_path(self, entity: str) -> Path:
        mapping = {
            "manufacturers": self.db_root / "registry" / "manufacturers.json",
            "mahajans": self.db_root / "registry" / "mahajans.json",
            "public_buyers": self.db_root / "registry" / "public_buyers.json",
            "workers": self.db_root / "registry" / "workers.json",
            "users_index": self.db_root / "registry" / "users_index.json",
        }
        target = mapping[entity]
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_catalog_path(self, entity: str) -> Path:
        mapping = {
            "products": self.db_root / "catalog" / "products.json",
            "product_approvals": self.db_root / "catalog" / "product_approvals.json",
            "raw_materials": self.db_root / "catalog" / "raw_materials.json",
            "categories": self.db_root / "catalog" / "categories.json",
            "image_refs": self.db_root / "catalog" / "image_refs.json",
        }
        target = mapping[entity]
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_order_path(self, order_type: str, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        normalized = str(order_type or "").strip().lower()
        target = self.db_root / "orders" / normalized / month / f"{normalized}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_notification_path(self, channel: str, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        normalized = str(channel or "").strip().lower()
        if normalized == "email_queue":
            target = self.db_root / "notifications" / "email_queue" / "gmail_queue.json"
        elif normalized == "dead_letter":
            target = self.db_root / "notifications" / "dead_letter" / "failed_notifications.json"
        elif normalized == "email_history":
            target = self.db_root / "notifications" / "email_history" / month / "sent_emails.json"
        else:
            target = self.db_root / "notifications" / "in_app_notifications" / month / "notifications.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_audit_path(self, year_month: str | None = None) -> Path:
        month = year_month or self.current_year_month()
        target = self.db_root / "audit" / month / "audit_logs.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_media_folder(self, entity_type: str) -> Path:
        normalized = str(entity_type or "").strip().lower()
        mapping = {
            "product": "products",
            "raw_material": "raw_materials",
            "payment_proof": "payment_proofs",
            "delivery_proof": "delivery_proofs",
        }
        target = self.db_root / "media" / mapping.get(normalized, normalized or "misc")
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_runtime_path(self, area: str) -> Path:
        target = self.runtime_root / area
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_config_path(self, name: str) -> Path:
        target = self.db_root / "config" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

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
