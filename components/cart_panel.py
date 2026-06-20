from __future__ import annotations

import streamlit as st

def render_cart_panel(cart: dict, *, cart_service, route: str, translator=None, pricing_summary: dict | None = None) -> bool:
    t = translator.t if translator else (lambda key: key)
    items = list(cart.get("items", []) or [])
    with st.container(border=True):
        st.markdown("### Cart")
        for index, item in enumerate(items):
            product_id = str(item.get("product_id", "")).strip()
            widget_suffix = str(item.get("cart_item_key", "")).strip() or product_id or f"row_{index}"
            cols = st.columns([3.8, 1.25, 1.1, 1.0], gap="small")
            product_code = str(item.get("product_code", "") or "").strip()
            category = " / ".join(
                part for part in [str(item.get("category", "")).strip(), str(item.get("subcategory", "")).strip()] if part
            )
            owner_name = str(item.get("owner_name", "") or "").strip()
            unit = str(item.get("unit", "") or "").strip()
            detail_parts = [part for part in [product_code, category, owner_name] if part]
            cols[0].markdown(f"**{item.get('product_name', '')}**")
            if detail_parts:
                cols[0].caption(" | ".join(detail_parts))
            quantity = cols[1].number_input(
                t("field.quantity"),
                min_value=1.0,
                step=1.0,
                value=float(item.get("quantity", 1) or 1),
                key=f"{route}_{widget_suffix}_cart_qty_{index}",
            )
            if float(quantity or 1) != float(item.get("quantity", 1) or 1):
                cart_service.set_quantity(
                    product_id,
                    quantity,
                    channel=str(item.get("channel", "") or "").strip().lower() or None,
                )
                st.rerun()
            cols[2].caption(f"Rs. {float(item.get('unit_price', 0) or 0):g}{f' / {unit}' if unit else ''}")
            cols[2].markdown(f"**Rs. {float(item.get('line_total', 0) or 0):g}**")
            if cols[3].button("Remove", use_container_width=True, key=f"{route}_{widget_suffix}_cart_remove_{index}"):
                cart_service.remove_item(
                    product_id,
                    channel=str(item.get("channel", "") or "").strip().lower() or None,
                )
                st.rerun()
        summary = dict(pricing_summary or {})
        items_total = float(summary.get("merchandise_total", cart_service.calculate_total()) or 0)
        packaging_charge = float(summary.get("packaging_charge", 0) or 0)
        shipping_charge = float(summary.get("shipping_charge", 0) or 0)
        total = float(summary.get("grand_total", items_total) or items_total)
        st.markdown("#### Price Details")
        st.caption(f"Items Total: Rs. {items_total:g}")
        st.caption(f"Packaging: Rs. {packaging_charge:g}")
        st.caption(f"Shipping: Rs. {shipping_charge:g}")
        st.markdown(f"**Total Amount: Rs. {total:g}**")
        return st.button("Proceed to Checkout", use_container_width=True, key=f"{route}_proceed_checkout")
