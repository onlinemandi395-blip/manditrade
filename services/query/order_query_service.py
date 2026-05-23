from __future__ import annotations
from pathlib import Path
from typing import Any

class OrderQueryService:
    def __init__(self, drive_service, json_service) -> None:
        self.drive_service = drive_service
        self.json_service = json_service

    def _list_order_files(self, manufacturer_code: str) -> list[Path]:
        orders_root = self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "orders"
        if not orders_root.exists():
            return []
        return sorted(orders_root.glob("*/*.json"))

    def list_orders(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return [self.json_service.read_json(path, {}) for path in self._list_order_files(manufacturer_code)]

    def list_orders_for_client(self, manufacturer_code: str, client_email: str) -> list[dict[str, Any]]:
        return [
            order for order in self.list_orders(manufacturer_code) 
            if order.get("client_email", "").lower() == client_email.lower()
        ]

    def get_order(self, manufacturer_code: str, order_id: str) -> dict[str, Any] | None:
        for order in self.list_orders(manufacturer_code):
            if order.get("order_id") == order_id:
                return order
        return None