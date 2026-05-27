from __future__ import annotations

import secrets
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ManufacturerOnboardingService:
    def __init__(self, drive_service, governance_service, safe_drive_write_service, json_service) -> None:
        self.drive_service = drive_service
        self.governance_service = governance_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service

    def generate_onboarding_secret(self) -> str:
        return f"MANU-SETUP-{secrets.token_urlsafe(18)}"

    def build_onboarding_steps(self, manufacturer: dict[str, Any]) -> str:
        code = manufacturer["manufacturer_code"]
        secret = manufacturer.get("manufacturer_onboarding_secret", "")
        owner_email = manufacturer.get("owner_email", "")
        return (
            f"Manufacturer onboarding for {code}\n\n"
            f"1. Sign in to MandiTrade with Google using {owner_email or 'the approved manufacturer email'}.\n"
            f"2. Share your manufacturer code with admin: {code}\n"
            f"3. Share your first-time manufacturer onboarding secret with admin: {secret}\n"
            f"4. Ask admin to map your Google account to this manufacturer workspace.\n"
            f"5. After admin approval, start with Products, Inventory, Clients, and Mandi RFQ.\n\n"
            f"Admin checklist:\n"
            f"- Verify Google email matches expected owner email.\n"
            f"- Confirm secret matches the onboarding packet.\n"
            f"- Mark manufacturer status as approved.\n"
            f"- Share post-approval navigation: Products, Inventory, Client Orders, Mandi RFQ, Ledger / Khata."
        )

    def create_manufacturer(self, *, manufacturer_code: str, manufacturer_name: str, owner_email: str, city: str, created_by: str, subscription_plan: str = "basic") -> dict[str, Any]:
        normalized_code = manufacturer_code.strip().upper()
        paths = self.drive_service.initialize_manufacturer_workspace(
            manufacturer_code=normalized_code,
            manufacturer_name=manufacturer_name.strip(),
            owner_email=owner_email.strip(),
            city=city.strip(),
            status="pending_approval",
        )
        onboarding_secret = self.generate_onboarding_secret()
        manufacturer = {
            "manufacturer_code": normalized_code,
            "manufacturer_name": manufacturer_name.strip(),
            "owner_email": owner_email.strip(),
            "city": city.strip(),
            "status": "pending_approval",
            "subscription_plan": subscription_plan,
            "manufacturer_onboarding_secret": onboarding_secret,
            "workspace_root": str(paths.manufacturer_root),
            "shared_zone": str(paths.shared_zone),
            "private_zone": str(paths.private_zone),
            "created_by": created_by,
            "created_at": datetime.now(UTC).isoformat(),
        }
        manufacturer["manufacturer_onboarding_steps"] = self.build_onboarding_steps(manufacturer)
        self.governance_service.register_manufacturer(manufacturer)
        self._sync_workspace_config(manufacturer)
        return manufacturer

    def update_manufacturer(self, manufacturer_code: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.governance_service.get_manufacturer(manufacturer_code)
        if current is None:
            raise ValueError(f"Manufacturer not found: {manufacturer_code}")
        merged = dict(current)
        merged.update({key: value for key, value in updates.items() if value is not None})
        merged["manufacturer_onboarding_steps"] = self.build_onboarding_steps(merged)
        updated = self.governance_service.update_manufacturer(manufacturer_code, merged)
        self._sync_workspace_config(updated)
        return updated

    def regenerate_secret(self, manufacturer_code: str) -> dict[str, Any]:
        secret = self.generate_onboarding_secret()
        return self.update_manufacturer(manufacturer_code, {"manufacturer_onboarding_secret": secret})

    def delete_manufacturer(self, manufacturer_code: str, *, remove_workspace: bool = False) -> bool:
        removed = self.governance_service.delete_manufacturer(manufacturer_code)
        if removed and remove_workspace:
            workspace_root = self.drive_service.get_manufacturer_paths(manufacturer_code).manufacturer_root
            if workspace_root.exists():
                shutil.rmtree(workspace_root)
        return removed

    def _sync_workspace_config(self, manufacturer: dict[str, Any]) -> None:
        config_path = self.drive_service.get_manufacturer_paths(manufacturer["manufacturer_code"]).private_zone / "manufacturer_config.json"
        payload = self.json_service.read_json(config_path, {"schema_version": "1.0"})
        payload.update(
            {
                "schema_version": "1.0",
                "manufacturer_code": manufacturer["manufacturer_code"],
                "manufacturer_name": manufacturer.get("manufacturer_name", ""),
                "owner_email": manufacturer.get("owner_email", ""),
                "city": manufacturer.get("city", ""),
                "status": manufacturer.get("status", "pending_approval"),
                "subscription_plan": manufacturer.get("subscription_plan", "basic"),
                "manufacturer_onboarding_secret": manufacturer.get("manufacturer_onboarding_secret", ""),
            }
        )
        self.safe_drive_write_service.replace_document(config_path, payload)
