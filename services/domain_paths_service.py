from __future__ import annotations

from pathlib import Path


class DomainPathsService:
    def __init__(self, drive_service) -> None:
        self.drive_service = drive_service

    def inventory_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"

    def orders_month_dir(self, manufacturer_code: str, year_month: str) -> Path:
        return self.drive_service.resolve_orders_month_dir(manufacturer_code, year_month)

    def client_order_path(self, manufacturer_code: str, order_id: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "client_orders" / f"{order_id}.json"

    def clients_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "clients.json"

    def ledger_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "ledgers.json"

    def notifications_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "notifications.json"

    def rfq_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "rfqs.json"

    def confirmations_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "trade_confirmations.json"
