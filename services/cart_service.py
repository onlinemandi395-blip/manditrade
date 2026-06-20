from __future__ import annotations

import streamlit as st

from services.pricing_service import PricingService


class CartService:
    def __init__(self) -> None:
        st.session_state.setdefault("mt_next_cart", {"items": []})
        self.pricing_service = PricingService()

    def _normalize_items(self) -> list[dict]:
        raw_items = list((st.session_state.get("mt_next_cart", {}) or {}).get("items", []) or [])
        merged_items: list[dict] = []
        merged_index: dict[str, dict] = {}
        anonymous_counter = 0
        for item in raw_items:
            product_id = str(item.get("product_id", "")).strip()
            if not product_id:
                anonymous_counter += 1
                product_id = f"cart-item-{anonymous_counter}"
            quantity = max(1.0, float(item.get("quantity", item.get("qty", 1)) or 1))
            unit_price = float(item.get("unit_price", item.get("price", 0)) or 0)
            product_name = str(item.get("product_name", "") or "").strip()
            existing = merged_index.get(product_id)
            if existing:
                existing["quantity"] += quantity
                existing["line_total"] = round(float(existing.get("unit_price", 0) or 0) * float(existing.get("quantity", 1) or 1), 2)
                continue
            normalized = {
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "channel": str(item.get("channel", "marketplace") or "marketplace"),
                "unit_price": unit_price,
                "line_total": round(unit_price * quantity, 2),
                "cart_item_key": str(item.get("cart_item_key", "")).strip() or product_id,
                "product_code": str(item.get("product_code", "") or "").strip(),
                "category": str(item.get("category", "") or "").strip(),
                "subcategory": str(item.get("subcategory", "") or "").strip(),
                "unit": str(item.get("unit", "") or "").strip(),
                "owner_name": str(item.get("owner_name", "") or "").strip(),
            }
            merged_items.append(normalized)
            merged_index[product_id] = normalized
        st.session_state["mt_next_cart"] = {"items": merged_items}
        return merged_items

    def add_to_cart(self, product: dict) -> None:
        self._normalize_items()
        sell_price = self.pricing_service.resolve_sell_price(product, "marketplace")
        product_id = str(product.get("product_id", "")).strip()
        existing = next(
            (
                item
                for item in st.session_state["mt_next_cart"]["items"]
                if str(item.get("product_id", "")).strip() == product_id
            ),
            None,
        )
        if existing:
            next_quantity = max(1.0, float(existing.get("quantity", 1) or 1) + 1.0)
            existing["quantity"] = next_quantity
            existing["unit_price"] = sell_price
            existing["line_total"] = round(float(sell_price or 0) * next_quantity, 2)
            return
        item = {
            "product_id": product_id,
            "product_name": product.get("product_name", ""),
            "quantity": 1.0,
            "channel": "marketplace",
            "unit_price": sell_price,
            "line_total": round(float(sell_price or 0), 2),
            "cart_item_key": product_id or f"cart-item-{len(st.session_state['mt_next_cart']['items']) + 1}",
            "product_code": str(product.get("product_code", product_id) or "").strip(),
            "category": str(product.get("category", "") or "").strip(),
            "subcategory": str(product.get("subcategory", "") or "").strip(),
            "unit": str(product.get("unit", "") or "").strip(),
            "owner_name": str(((product.get("owner") or {}).get("display_name", "")) or "").strip(),
        }
        st.session_state["mt_next_cart"]["items"].append(item)

    def set_quantity(self, product_id: str, quantity: float) -> None:
        self._normalize_items()
        normalized_id = str(product_id or "").strip()
        for item in st.session_state["mt_next_cart"]["items"]:
            if str(item.get("product_id", "")).strip() != normalized_id:
                continue
            normalized_quantity = max(1.0, float(quantity or 1))
            item["quantity"] = normalized_quantity
            item["line_total"] = round(float(item.get("unit_price", 0) or 0) * normalized_quantity, 2)
            return

    def remove_item(self, product_id: str) -> None:
        self._normalize_items()
        st.session_state["mt_next_cart"]["items"] = [item for item in st.session_state["mt_next_cart"]["items"] if item.get("product_id") != product_id]

    def clear_cart(self) -> None:
        st.session_state["mt_next_cart"] = {"items": []}

    def get_cart(self) -> dict:
        return {"items": self._normalize_items()}

    def calculate_total(self) -> float:
        return round(
            sum(
                float(item.get("line_total", 0) or 0)
                if "line_total" in item
                else float(item.get("unit_price", 0) or 0) * int(item.get("quantity", item.get("qty", 0)) or 0)
                for item in self.get_cart()["items"]
            ),
            2,
        )
