from __future__ import annotations

import streamlit as st

from services.pricing_service import PricingService


class CartService:
    def __init__(self) -> None:
        st.session_state.setdefault("mt_next_cart", {"items": []})
        self.pricing_service = PricingService()

    def add_to_cart(self, product: dict) -> None:
        sell_price = self.pricing_service.resolve_sell_price(product, "marketplace")
        item = {
            "product_id": product.get("product_id", ""),
            "product_name": product.get("product_name", ""),
            "quantity": 1,
            "channel": "marketplace",
            "unit_price": sell_price,
            "line_total": sell_price,
        }
        st.session_state["mt_next_cart"]["items"].append(item)

    def set_quantity(self, product_id: str, quantity: float) -> None:
        normalized_id = str(product_id or "").strip()
        for item in st.session_state["mt_next_cart"]["items"]:
            if str(item.get("product_id", "")).strip() != normalized_id:
                continue
            normalized_quantity = max(1.0, float(quantity or 1))
            item["quantity"] = normalized_quantity
            item["line_total"] = round(float(item.get("unit_price", 0) or 0) * normalized_quantity, 2)
            return

    def remove_item(self, product_id: str) -> None:
        st.session_state["mt_next_cart"]["items"] = [item for item in st.session_state["mt_next_cart"]["items"] if item.get("product_id") != product_id]

    def clear_cart(self) -> None:
        st.session_state["mt_next_cart"] = {"items": []}

    def get_cart(self) -> dict:
        return st.session_state["mt_next_cart"]

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
