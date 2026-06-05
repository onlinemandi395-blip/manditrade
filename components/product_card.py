from __future__ import annotations

import streamlit as st


def render_product_card(product: dict, *, view: str = "marketplace", on_add_to_cart=None) -> None:
    image_url = str(product.get("image_url", "") or "").strip()
    marketplace = (product.get("sales_channels") or {}).get("marketplace", {})
    manditrade = (product.get("sales_channels") or {}).get("manditrade", {})
    manufacturer_count = len([tag for tag in product.get("manufacturer_tags", []) if tag.get("active", True)])
    mahajan_count = len([tag for tag in product.get("mahajan_tags", []) if tag.get("active", True)])
    with st.container(border=True):
        media = st.empty()
        if image_url:
            media.image(image_url, use_container_width=True)
        else:
            media.markdown("<div class='mt-product-card__media'>No Image</div>", unsafe_allow_html=True)
        st.markdown(f"#### {product.get('product_name', product.get('product_id', 'Product'))}")
        st.caption(f"{product.get('category', 'General')} | {product.get('status', 'ACTIVE')}")
        if view == "marketplace":
            st.write(f"Marketplace Price: {marketplace.get('price', 0)}")
            if st.button("Add to Cart", key=f"cart_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        elif view == "manditrade":
            st.write(f"MandiTrade Price: {manditrade.get('price', 0)}")
            st.caption(f"Manufacturers: {manufacturer_count} | Mahajans: {mahajan_count}")
            st.button("Request / Order", key=f"request_{product.get('product_id', '')}", use_container_width=True)
        else:
            st.write(f"Marketplace: {'On' if marketplace.get('enabled') else 'Off'} | Price: {marketplace.get('price', 0)}")
            st.write(f"MandiTrade: {'On' if manditrade.get('enabled') else 'Off'} | Price: {manditrade.get('price', 0)}")
            st.caption(f"Manufacturers: {manufacturer_count} | Mahajans: {mahajan_count}")
