from __future__ import annotations

from typing import Any


class DualInventoryService:
    def __init__(self, safe_drive_write_service, json_service, domain_paths_service) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.domain_paths = domain_paths_service

    def _default_doc(self, manufacturer_code: str) -> dict[str, Any]:
        return {"schema_version": "2.0", "manufacturer_code": manufacturer_code, "items": []}

    def list_inventory(self, manufacturer_code: str) -> dict[str, Any]:
        return self.json_service.read_json(self.domain_paths.inventory_path(manufacturer_code), self._default_doc(manufacturer_code))

    def upsert_inventory_item(
        self,
        manufacturer_code: str,
        *,
        product_id: str,
        product_name: str,
        unit: str,
        self_available_qty: int = 0,
        mandi_available_qty: int = 0,
        visible_to_mandi: bool = True,
    ) -> None:
        path = self.domain_paths.inventory_path(manufacturer_code)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "2.0")
            payload.setdefault("manufacturer_code", manufacturer_code)
            payload.setdefault("items", [])
            record = next((item for item in payload["items"] if item.get("product_id") == product_id), None)
            if record is None:
                payload["items"].append(
                    {
                        "manufacturer_id": manufacturer_code,
                        "product_id": product_id,
                        "product_name": product_name,
                        "self_inventory": {"available_qty": int(self_available_qty), "reserved_qty": 0, "unit": unit},
                        "mandi_inventory": {
                            "available_qty": int(mandi_available_qty),
                            "reserved_qty": 0,
                            "unit": unit,
                            "visible_to_mandi": bool(visible_to_mandi),
                        },
                    }
                )
            else:
                record["product_name"] = product_name
                record.setdefault("self_inventory", {"available_qty": 0, "reserved_qty": 0, "unit": unit})
                record.setdefault("mandi_inventory", {"available_qty": 0, "reserved_qty": 0, "unit": unit, "visible_to_mandi": bool(visible_to_mandi)})
                record["self_inventory"]["available_qty"] = int(self_available_qty)
                record["self_inventory"]["unit"] = unit
                record["mandi_inventory"]["available_qty"] = int(mandi_available_qty)
                record["mandi_inventory"]["unit"] = unit
                record["mandi_inventory"]["visible_to_mandi"] = bool(visible_to_mandi)
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")

    def reserve_self_inventory(self, manufacturer_code: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._reserve(manufacturer_code, items, bucket="self_inventory")

    def reserve_mandi_inventory(self, manufacturer_code: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._reserve(manufacturer_code, items, bucket="mandi_inventory")

    def _reserve(self, manufacturer_code: str, items: list[dict[str, Any]], *, bucket: str) -> dict[str, Any]:
        path = self.domain_paths.inventory_path(manufacturer_code)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "2.0")
            payload.setdefault("items", [])
            for item in items:
                record = next((entry for entry in payload["items"] if entry.get("product_id") == item["product_id"]), None)
                if record is None:
                    raise ValueError(f"Inventory record not found for {item['product_id']}")
                pocket = record[bucket]
                requested = int(item["qty"])
                available = int(pocket.get("available_qty", 0)) - int(pocket.get("reserved_qty", 0))
                if available < requested:
                    raise ValueError(f"Insufficient {bucket} for {item['product_id']}")
                pocket["reserved_qty"] = int(pocket.get("reserved_qty", 0)) + requested
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        return self.list_inventory(manufacturer_code)

    def release_reserved(self, manufacturer_code: str, items: list[dict[str, Any]], *, bucket: str) -> dict[str, Any]:
        path = self.domain_paths.inventory_path(manufacturer_code)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in items:
                record = next((entry for entry in payload.get("items", []) if entry.get("product_id") == item["product_id"]), None)
                if record:
                    record[bucket]["reserved_qty"] = max(0, int(record[bucket].get("reserved_qty", 0)) - int(item["qty"]))
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        return self.list_inventory(manufacturer_code)

    def finalize_reserved(self, manufacturer_code: str, items: list[dict[str, Any]], *, bucket: str) -> dict[str, Any]:
        path = self.domain_paths.inventory_path(manufacturer_code)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in items:
                record = next((entry for entry in payload.get("items", []) if entry.get("product_id") == item["product_id"]), None)
                if record:
                    pocket = record[bucket]
                    qty = int(item["qty"])
                    pocket["reserved_qty"] = max(0, int(pocket.get("reserved_qty", 0)) - qty)
                    pocket["available_qty"] = max(0, int(pocket.get("available_qty", 0)) - qty)
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        return self.list_inventory(manufacturer_code)

    def transfer_self_to_mandi(self, manufacturer_code: str, product_id: str, qty: int) -> dict[str, Any]:
        return self._transfer(manufacturer_code, product_id, qty, from_bucket="self_inventory", to_bucket="mandi_inventory")

    def withdraw_mandi_to_self(self, manufacturer_code: str, product_id: str, qty: int) -> dict[str, Any]:
        return self._transfer(manufacturer_code, product_id, qty, from_bucket="mandi_inventory", to_bucket="self_inventory")

    def _transfer(self, manufacturer_code: str, product_id: str, qty: int, *, from_bucket: str, to_bucket: str) -> dict[str, Any]:
        path = self.domain_paths.inventory_path(manufacturer_code)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            record = next((entry for entry in payload.get("items", []) if entry.get("product_id") == product_id), None)
            if record is None:
                raise ValueError(f"Inventory record not found for {product_id}")
            source = record[from_bucket]
            available = int(source.get("available_qty", 0)) - int(source.get("reserved_qty", 0))
            if available < int(qty):
                raise ValueError(f"Insufficient transferable stock for {product_id}")
            source["available_qty"] = int(source.get("available_qty", 0)) - int(qty)
            record[to_bucket]["available_qty"] = int(record[to_bucket].get("available_qty", 0)) + int(qty)
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        return self.list_inventory(manufacturer_code)
