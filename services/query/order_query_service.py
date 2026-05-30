from __future__ import annotations
from pathlib import Path
from typing import Any

class OrderQueryService:
    def __init__(self, drive_service, json_service, domain_paths_service=None) -> None:
        self.drive_service = drive_service
        self.json_service = json_service
        self.domain_paths = domain_paths_service

    def _list_order_files(self, manufacturer_code: str) -> list[Path]:
        orders_root = self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "client_orders"
        if not orders_root.exists():
            return []
        return sorted(orders_root.glob("*.json"))

    def list_orders(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return [self.json_service.read_json(path, {}) for path in self._list_order_files(manufacturer_code)]

    def list_orders_for_client(self, manufacturer_code: str, client_email: str) -> list[dict[str, Any]]:
        rows = []
        for order in self.list_orders(manufacturer_code):
            if order.get("client_email", "").lower() != client_email.lower():
                continue
            sanitized = dict(order)
            sanitized.pop("commission_breakdown", None)
            sanitized_items = []
            for item in sanitized.get("items", []):
                clean = dict(item)
                clean.pop("mandi_price", None)
                clean.pop("marketplace_price", None)
                clean.pop("sale_price", None)
                clean["your_price"] = clean.get("client_price", clean.get("mrp", 0))
                sanitized_items.append(clean)
            sanitized["items"] = sanitized_items
            rows.append(sanitized)
        return rows

    def get_order(self, manufacturer_code: str, order_id: str) -> dict[str, Any] | None:
        for order in self.list_orders(manufacturer_code):
            if order.get("order_id") == order_id:
                return order
        return None

    def summarize_orders(self, manufacturer_code: str) -> dict[str, Any]:
        orders = self.list_orders(manufacturer_code)
        status_counts: dict[str, int] = {}
        total_value = 0.0
        for order in orders:
            status = str(order.get("status") or "UNKNOWN").strip().upper()
            status_counts[status] = status_counts.get(status, 0) + 1
            total_value += float(order.get("grand_total", order.get("total_amount", 0)) or 0)
        return {
            "manufacturer_code": manufacturer_code,
            "total_orders": len(orders),
            "status_counts": status_counts,
            "total_value": round(total_value, 2),
        }
