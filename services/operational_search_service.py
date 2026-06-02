from __future__ import annotations

from typing import Any

from utils.deep_links import build_deep_link_target


class OperationalSearchService:
    def search(self, app_context: dict, query: str) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        if not normalized:
            return []
        results: list[dict[str, Any]] = []
        governance = app_context["governance_service"]
        for manufacturer in governance.list_manufacturers():
            if normalized in str(manufacturer.get("manufacturer_code", "")).lower() or normalized in str(manufacturer.get("business_name", "")).lower():
                results.append({"label": manufacturer.get("business_name", manufacturer.get("manufacturer_code", "")), "entity_type": "manufacturer", "entity_id": manufacturer.get("manufacturer_code", ""), "target": {"route": "Manufacturers", "source_id": manufacturer.get("manufacturer_code", "")}})
        for mahajan in governance.list_mahajans():
            if normalized in str(mahajan.get("mahajan_id", "")).lower() or normalized in str(mahajan.get("business_name", "")).lower():
                results.append({"label": mahajan.get("business_name", mahajan.get("mahajan_id", "")), "entity_type": "mahajan", "entity_id": mahajan.get("mahajan_id", ""), "target": {"route": "Mahajans", "source_id": mahajan.get("mahajan_id", "")}})
        for product in governance.list_products():
            if normalized in str(product.get("product_id", "")).lower() or normalized in str(product.get("name", "")).lower():
                results.append({"label": product.get("name", product.get("product_id", "")), "entity_type": "product", "entity_id": product.get("product_id", ""), "target": build_deep_link_target("PRODUCT_PROPOSAL", product.get("product_id", ""))})
        for item in governance.list_raw_materials():
            if normalized in str(item.get("raw_material_id", "")).lower() or normalized in str(item.get("name", "")).lower():
                results.append({"label": item.get("name", item.get("raw_material_id", "")), "entity_type": "raw_material", "entity_id": item.get("raw_material_id", ""), "target": {"route": "Raw Materials", "source_id": item.get("raw_material_id", "")}})
        for order in governance.list_supply_orders():
            if normalized in str(order.get("mandi_order_id", "")).lower():
                results.append({"label": order.get("mandi_order_id", ""), "entity_type": "supply_order", "entity_id": order.get("mandi_order_id", ""), "target": build_deep_link_target("SUPPLY_ORDER", order.get("mandi_order_id", ""))})
        for order in app_context["public_order_service"].list_all_orders():
            if normalized in str(order.get("public_order_id", "")).lower():
                results.append({"label": order.get("public_order_id", ""), "entity_type": "public_order", "entity_id": order.get("public_order_id", ""), "target": build_deep_link_target("PUBLIC_ORDER", order.get("public_order_id", ""))})
        for manufacturer in governance.list_manufacturers():
            for entry in app_context["ledger_service"].list_ledger_entries(manufacturer.get("manufacturer_code", "")):
                if normalized in str(entry.get("entry_id", "")).lower():
                    results.append({"label": entry.get("entry_id", ""), "entity_type": "ledger_entry", "entity_id": entry.get("entry_id", ""), "target": build_deep_link_target("LEDGER", entry.get("entry_id", ""))})
        return results[:25]
