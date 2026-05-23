from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from services.json_service import JsonService


@dataclass(slots=True)
class ManufacturerPaths:
    manufacturer_root: Path
    shared_zone: Path
    private_zone: Path


class DriveService:
    def __init__(
        self,
        local_root: Path,
        manufacturer_root_prefix: str,
        shared_zone_name: str,
        private_zone_name: str,
        use_drive_api: bool = False,
        safe_drive_write_service=None,
        logging_service=None,
        runtime_metrics_service=None,
    ) -> None:
        self.local_root = local_root
        self.manufacturer_root_prefix = manufacturer_root_prefix
        self.shared_zone_name = shared_zone_name
        self.private_zone_name = private_zone_name
        self.use_drive_api = use_drive_api
        self.json_service = JsonService()
        self.safe_drive_write_service = safe_drive_write_service
        self.logging_service = logging_service
        self.runtime_metrics_service = runtime_metrics_service

    def build_drive_client(self, credentials: Credentials):
        return build("drive", "v3", credentials=credentials)

    def retry(self, operation, retries: int = 3, base_delay: float = 0.5):
        for attempt in range(retries):
            started = time.perf_counter()
            try:
                result = operation()
                if self.runtime_metrics_service:
                    self.runtime_metrics_service.increment("drive_retry_success", extra={"attempt": attempt + 1, "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
                return result
            except Exception as exc:
                if self.logging_service:
                    self.logging_service.log_error("drive_failures", "Drive retry attempt failed", {"attempt": attempt + 1, "error": str(exc)})
                if self.runtime_metrics_service:
                    self.runtime_metrics_service.increment("drive_retry_failures", extra={"attempt": attempt + 1, "error": str(exc)})
                if attempt == retries - 1:
                    raise
                time.sleep(base_delay * (2**attempt))

    def get_manufacturer_paths(self, manufacturer_code: str) -> ManufacturerPaths:
        root_name = f"{self.manufacturer_root_prefix}{manufacturer_code}"
        manufacturer_root = self.local_root / root_name
        return ManufacturerPaths(
            manufacturer_root=manufacturer_root,
            shared_zone=manufacturer_root / self.shared_zone_name,
            private_zone=manufacturer_root / self.private_zone_name,
        )

    def initialize_manufacturer_workspace(
        self,
        manufacturer_code: str,
        manufacturer_name: str,
        owner_email: str | None = None,
        status: str = "pending_approval",
        city: str | None = None,
    ) -> ManufacturerPaths:
        paths = self.get_manufacturer_paths(manufacturer_code)
        paths.shared_zone.mkdir(parents=True, exist_ok=True)
        paths.private_zone.mkdir(parents=True, exist_ok=True)
        (paths.private_zone / "invoices").mkdir(exist_ok=True)
        (paths.private_zone / "payments").mkdir(exist_ok=True)
        (paths.private_zone / "client_orders").mkdir(exist_ok=True)
        (paths.private_zone / "client_profiles").mkdir(exist_ok=True)
        (paths.shared_zone / "orders").mkdir(exist_ok=True)

        shared_files: dict[str, Any] = {
            "inventory.json": {"manufacturer_code": manufacturer_code, "items": []},
            "procurement.json": {"manufacturer_code": manufacturer_code, "requests": []},
            "agreements.json": {"manufacturer_code": manufacturer_code, "agreements": []},
            "wallet_summary.json": {"manufacturer_code": manufacturer_code, "balance": 0, "currency": "INR"},
            "subscription.json": {"manufacturer_code": manufacturer_code, "plan_code": "basic", "status": "active"},
        }
        private_files: dict[str, Any] = {
            "clients.json": {"manufacturer_code": manufacturer_code, "clients": []},
            "api_keys.json": {"manufacturer_code": manufacturer_code, "keys": []},
            "manufacturer_config.json": {
                "manufacturer_code": manufacturer_code,
                "manufacturer_name": manufacturer_name,
                "owner_email": owner_email or "",
                "city": city or "",
                "status": status,
            },
        }

        for file_name, payload in shared_files.items():
            document = {"schema_version": "1.0", **payload}
            schema_name = "inventory" if file_name == "inventory.json" else "procurement" if file_name == "procurement.json" else None
            self.safe_drive_write_service.replace_document(paths.shared_zone / file_name, document, schema_name=schema_name)
        for file_name, payload in private_files.items():
            document = {"schema_version": "1.0", **payload}
            schema_name = "clients" if file_name == "clients.json" else None
            self.safe_drive_write_service.replace_document(paths.private_zone / file_name, document, schema_name=schema_name)

        report_path = paths.private_zone / "business_reports.csv"
        if not report_path.exists():
            report_path.write_text("report_date,revenue_inr,orders_count\n", encoding="utf-8")
        return paths

    def list_manufacturer_workspaces(self) -> list[dict[str, str]]:
        if not self.local_root.exists():
            return []
        workspaces = []
        for path in sorted(self.local_root.iterdir()):
            if path.is_dir():
                workspaces.append({"folder_name": path.name, "path": str(path)})
        return workspaces

    def describe_runtime_mode(self) -> str:
        return "google_drive_runtime" if self.use_drive_api else "local_mirror_bootstrap"

    def validate_private_zone_access(self, role: str, manufacturer_code: str | None, target_manufacturer_code: str) -> bool:
        if role == "admin":
            return False
        if role == "manufacturer":
            return manufacturer_code == target_manufacturer_code
        if role == "client":
            return manufacturer_code == target_manufacturer_code
        return False

    def resolve_orders_month_dir(self, manufacturer_code: str, year_month: str) -> Path:
        paths = self.get_manufacturer_paths(manufacturer_code)
        month_dir = paths.shared_zone / "orders" / year_month
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir
