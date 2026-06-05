from __future__ import annotations

from typing import Any


class IdentityGovernanceService:
    MANUFACTURER_FIELDS = (
        "business_name",
        "brand_name",
        "contact_person",
        "owner_email",
        "mobile",
        "address.line1",
        "address.city",
        "address.state",
        "address.pin_code",
        "legal.gstin",
        "legal.pan",
        "banking.account_holder_name",
        "banking.account_number",
        "banking.ifsc",
    )
    MAHAJAN_FIELDS = (
        "business_name",
        "owner_name",
        "email",
        "mobile",
        "city",
        "coverage_area",
        "states_served",
        "raw_material_categories",
        "minimum_order_qty",
    )
    WORKER_FIELDS = (
        "name",
        "linked_email",
        "mobile",
        "city",
        "state",
        "skills",
        "availability_status",
        "daily_rate",
    )

    def __init__(self, trust_badge_service) -> None:
        self.trust_badge_service = trust_badge_service

    def summarize_manufacturer(self, manufacturer: dict[str, Any]) -> dict[str, Any]:
        summary = dict(manufacturer)
        summary["status"] = self._normalized_status(manufacturer.get("status"), default="PENDING")
        summary["completion_score"] = self.completion_score("manufacturer", manufacturer)
        summary["verification_badges"] = self.trust_badge_service.verification_badges(manufacturer)
        summary["trust_tier"] = self.trust_badge_service.identity_tier(manufacturer)
        summary["trust_badges"] = self.trust_badge_service.badges_for_manufacturer(manufacturer)
        summary["location"] = ", ".join(
            part for part in [
                str((manufacturer.get("address") or {}).get("city") or manufacturer.get("city") or "").strip(),
                str((manufacturer.get("address") or {}).get("state") or "").strip(),
            ] if part
        )
        return summary

    def summarize_mahajan(self, mahajan: dict[str, Any]) -> dict[str, Any]:
        summary = dict(mahajan)
        summary["status"] = self._normalized_status(mahajan.get("status"), default="PENDING")
        summary["completion_score"] = self.completion_score("mahajan", mahajan)
        summary["verification_badges"] = self.trust_badge_service.verification_badges(mahajan)
        summary["trust_tier"] = self.trust_badge_service.identity_tier(mahajan)
        summary["trust_badges"] = self.trust_badge_service.badges_for_supplier_summary(mahajan)
        summary["location"] = ", ".join(
            part for part in [
                str(mahajan.get("city") or "").strip(),
                str(mahajan.get("coverage_area") or "").strip(),
            ] if part
        )
        return summary

    def summarize_worker(self, worker: dict[str, Any]) -> dict[str, Any]:
        summary = dict(worker)
        summary["status"] = self._normalized_status(worker.get("status"), default="PENDING")
        summary["completion_score"] = self.completion_score("worker", worker)
        summary["verification_badges"] = self.trust_badge_service.verification_badges(worker)
        summary["trust_tier"] = self.trust_badge_service.identity_tier(worker)
        summary["trust_badges"] = self.trust_badge_service.badges_for_supplier_summary(worker)
        summary["location"] = ", ".join(
            part for part in [
                str(worker.get("city") or "").strip(),
                str(worker.get("state") or "").strip(),
            ] if part
        )
        return summary

    def completion_score(self, role: str, entity: dict[str, Any]) -> int:
        field_map = {
            "manufacturer": self.MANUFACTURER_FIELDS,
            "mahajan": self.MAHAJAN_FIELDS,
            "worker": self.WORKER_FIELDS,
        }
        required_fields = field_map.get(role, ())
        if not required_fields:
            return 0
        completed = sum(1 for field_name in required_fields if self._has_value(entity, field_name))
        ratio = completed / len(required_fields)
        return min(100, int(ratio * 4) * 25)

    def readiness_counts(self, role: str, rows: list[dict[str, Any]]) -> dict[str, int]:
        summaries = [self._summarize(role, row) for row in rows]
        return {
            "total": len(summaries),
            "pending": len([row for row in summaries if row.get("status") == "PENDING"]),
            "active": len([row for row in summaries if row.get("status") == "ACTIVE"]),
            "blocked": len([row for row in summaries if row.get("status") in {"BLOCKED", "SUSPENDED"}]),
            "archived": len([row for row in summaries if row.get("status") == "ARCHIVED"]),
            "trusted": len([row for row in summaries if row.get("trust_tier") == "Trusted"]),
        }

    def status_bucket(self, row: dict[str, Any]) -> str:
        status = self._normalized_status(row.get("status"), default="PENDING")
        if status in {"BLOCKED", "SUSPENDED"}:
            return "BLOCKED"
        return status

    def _summarize(self, role: str, row: dict[str, Any]) -> dict[str, Any]:
        if role == "manufacturer":
            return self.summarize_manufacturer(row)
        if role == "mahajan":
            return self.summarize_mahajan(row)
        return self.summarize_worker(row)

    def _has_value(self, entity: dict[str, Any], dotted_key: str) -> bool:
        current: Any = entity
        for part in dotted_key.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
                break
        if isinstance(current, list):
            return bool([item for item in current if str(item).strip()])
        if isinstance(current, bool):
            return current
        if isinstance(current, (int, float)):
            return current > 0
        return bool(str(current or "").strip())

    def _normalized_status(self, status: Any, *, default: str) -> str:
        normalized = str(status or default).strip().upper()
        if normalized == "INVITED":
            return "PENDING"
        if normalized == "INACTIVE":
            return "SUSPENDED"
        return normalized or default
