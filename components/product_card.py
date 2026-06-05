from __future__ import annotations

import streamlit as st


def render_product_card(product: dict, *, on_add_to_cart=None) -> None:
    image_url = ""
    for image in product.get("images", []) or []:
        image_url = image.get("thumbnail_url") or image.get("view_url") or ""
        if image_url:
            break
    price = ((product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0)
    with st.container(border=True):
        media = st.empty()
        if image_url:
            media.image(image_url, use_container_width=True)
        else:
            media.markdown("<div class='mt-product-card__media'>No Image</div>", unsafe_allow_html=True)
        st.markdown(f"#### {product.get('product_name', product.get('product_id', 'Product'))}")
        st.caption(product.get("category", "General"))
        st.write(f"Price: {price}")
        cols = st.columns(2)
        if cols[0].button("Add to Cart", key=f"cart_{product.get('product_id', '')}", use_container_width=True):
            if on_add_to_cart:
                on_add_to_cart(product)
        cols[1].button("View Details", key=f"detail_{product.get('product_id', '')}", use_container_width=True)
