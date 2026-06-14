from __future__ import annotations

import streamlit as st


def render_cart_panel(cart: dict, *, cart_service, route: str, translator=None) -> bool:
    t = translator.t if translator else (lambda key: key)
    items = list(cart.get("items", []) or [])
    st.markdown("<div class='mt-commerce-summary'>", unsafe_allow_html=True)
    st.markdown("### Cart")
    for item in items:
        product_id = str(item.get("product_id", "")).strip()
        cols = st.columns([3.2, 1.1, 1.3, 0.9], gap="small")
        cols[0].markdown(f"**{item.get('product_name', '')}**")
        quantity = cols[1].number_input(
            t("field.quantity"),
            min_value=1.0,
            step=1.0,
            value=float(item.get("quantity", 1) or 1),
            key=f"{route}_{product_id}_cart_qty",
        )
        if float(quantity or 1) != float(item.get("quantity", 1) or 1):
            cart_service.set_quantity(product_id, quantity)
            st.rerun()
        cols[2].caption(f"Rs. {float(item.get('line_total', 0) or 0):g}")
        if cols[3].button("Remove", use_container_width=True, key=f"{route}_{product_id}_cart_remove"):
            cart_service.remove_item(product_id)
            st.rerun()
    total = cart_service.calculate_total()
    st.markdown(f"#### Price Details")
    st.caption(f"Items Total: Rs. {total:g}")
    st.caption("Delivery Fee: Rs. 0")
    st.markdown(f"**Total Amount: Rs. {total:g}**")
    proceed = st.button("Proceed to Checkout", use_container_width=True, key=f"{route}_proceed_checkout")
    st.markdown("</div>", unsafe_allow_html=True)
    return proceed
