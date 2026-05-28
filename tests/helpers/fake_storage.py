from __future__ import annotations

import json
from pathlib import Path


class JsonServiceStub:
    def read_json(self, path: Path, default):
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ManufacturerPaths:
    def __init__(self, root: Path):
        self.root = root
        self.manufacturer_root = root
        self.shared_zone = root / "shared_zone"
        self.private_zone = root / "private_zone"


class DriveStub:
    def __init__(self, root: Path, json_service: JsonServiceStub):
        self.root = root
        self.json_service = json_service
        self.safe_drive_write_service = None

    def get_manufacturer_paths(self, manufacturer_code: str):
        root = self.root / manufacturer_code
        paths = ManufacturerPaths(root)
        paths.shared_zone.mkdir(parents=True, exist_ok=True)
        (paths.private_zone / "client_orders").mkdir(parents=True, exist_ok=True)
        (paths.private_zone / "invoices").mkdir(parents=True, exist_ok=True)
        (paths.private_zone / "delivery_proofs").mkdir(parents=True, exist_ok=True)
        (paths.private_zone / "payments").mkdir(parents=True, exist_ok=True)
        return paths

    def initialize_manufacturer_workspace(
        self,
        manufacturer_code: str,
        manufacturer_name: str,
        owner_email: str | None = None,
        status: str = "ACTIVE",
        city: str | None = None,
    ):
        paths = self.get_manufacturer_paths(manufacturer_code)
        self.json_service.write_json(
            paths.private_zone / "manufacturer_config.json",
            {
                "schema_version": "1.0",
                "manufacturer_id": "",
                "manufacturer_code": manufacturer_code,
                "business_name": manufacturer_name,
                "manufacturer_name": manufacturer_name,
                "owner_name": "",
                "owner_email": owner_email or "",
                "mobile": "",
                "alternate_mobile": "",
                "address": {"line1": "", "line2": "", "city": city or "", "state": "", "pin_code": ""},
                "city": city or "",
                "business_type": "",
                "product_categories": [],
                "legal": {"udyam_id": "", "gstin": "", "pan": "", "aadhaar": ""},
                "banking": {"account_holder_name": "", "account_number": "", "ifsc": "", "upi_id": ""},
                "google_drive_connected_status": "NOT_CONNECTED",
                "business_description": "",
                "status": status,
            },
        )
        return paths

    def resolve_orders_month_dir(self, manufacturer_code: str, month_key: str) -> Path:
        target = self.get_manufacturer_paths(manufacturer_code).shared_zone / "orders" / month_key
        target.mkdir(parents=True, exist_ok=True)
        return target
