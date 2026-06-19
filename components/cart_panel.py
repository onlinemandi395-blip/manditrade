from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


def render_cart_panel(cart: dict, *, cart_service, route: str, translator=None) -> bool:
    t = translator.t if translator else (lambda key: key)
    items = list(cart.get("items", []) or [])
    render_template("cart_summary_open.html")
    st.markdown("### Cart")
    for index, item in enumerate(items):
        product_id = str(item.get("product_id", "")).strip()
        widget_suffix = str(item.get("cart_item_key", "")).strip() or product_id or f"row_{index}"
        cols = st.columns([3.2, 1.1, 1.3, 0.9], gap="small")
        cols[0].markdown(f"**{item.get('product_name', '')}**")
        quantity = cols[1].number_input(
            t("field.quantity"),
            min_value=1.0,
            step=1.0,
            value=float(item.get("quantity", 1) or 1),
            key=f"{route}_{widget_suffix}_cart_qty_{index}",
        )
        if float(quantity or 1) != float(item.get("quantity", 1) or 1):
            cart_service.set_quantity(product_id, quantity)
            st.rerun()
        cols[2].caption(f"Rs. {float(item.get('line_total', 0) or 0):g}")
        if cols[3].button("Remove", use_container_width=True, key=f"{route}_{widget_suffix}_cart_remove_{index}"):
            cart_service.remove_item(product_id)
            st.rerun()
    total = cart_service.calculate_total()
    st.markdown(f"#### Price Details")
    st.caption(f"Items Total: Rs. {total:g}")
    st.caption("Delivery Fee: Rs. 0")
    st.markdown(f"**Total Amount: Rs. {total:g}**")
    proceed = st.button("Proceed to Checkout", use_container_width=True, key=f"{route}_proceed_checkout")
    render_template("html_close_div.html")
    return proceed
