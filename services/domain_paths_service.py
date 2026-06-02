from __future__ import annotations

from pathlib import Path


class DomainPathsService:
    def __init__(self, drive_service, drive_path_service=None) -> None:
        self.drive_service = drive_service
        self.drive_path_service = drive_path_service

    def inventory_path(self, manufacturer_code: str) -> Path:
        return self.private_self_inventory_path(manufacturer_code)

    def private_self_inventory_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "inventory.json"

    def shared_mandi_inventory_projection_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"

    def orders_month_dir(self, manufacturer_code: str, year_month: str) -> Path:
        return self.drive_service.resolve_orders_month_dir(manufacturer_code, year_month)

    def shared_client_orders_month_dir(self, manufacturer_code: str, year_month: str) -> Path:
        return self.drive_service.resolve_orders_month_dir(manufacturer_code, year_month)

    def shared_client_order_projection_path(self, manufacturer_code: str, year_month: str, order_id: str) -> Path:
        return self.shared_client_orders_month_dir(manufacturer_code, year_month) / f"{order_id}.json"

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

    def registry_path(self, entity: str) -> Path:
        if not self.drive_path_service:
            raise ValueError("Drive path service not configured.")
        return self.drive_path_service.get_registry_path(entity)

    def catalog_path(self, entity: str) -> Path:
        if not self.drive_path_service:
            raise ValueError("Drive path service not configured.")
        return self.drive_path_service.get_catalog_path(entity)

    def notification_channel_path(self, channel: str, year_month: str | None = None) -> Path:
        if not self.drive_path_service:
            raise ValueError("Drive path service not configured.")
        return self.drive_path_service.get_notification_path(channel, year_month)
