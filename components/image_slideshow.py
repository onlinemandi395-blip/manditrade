from __future__ import annotations

import streamlit as st


SLIDESHOW_PRODUCT_KEY = "active_slideshow_product_id"
SLIDESHOW_INDEX_KEY = "active_slideshow_index"
SLIDESHOW_RETURN_ROUTE_KEY = "return_route"


def open_slideshow(*, product_id: str, return_route: str) -> None:
    st.session_state[SLIDESHOW_PRODUCT_KEY] = str(product_id or "").strip()
    st.session_state[SLIDESHOW_INDEX_KEY] = 0
    st.session_state[SLIDESHOW_RETURN_ROUTE_KEY] = str(return_route or "").strip()


def close_slideshow() -> None:
    st.session_state.pop(SLIDESHOW_PRODUCT_KEY, None)
    st.session_state.pop(SLIDESHOW_INDEX_KEY, None)


def is_slideshow_active() -> bool:
    return bool(str(st.session_state.get(SLIDESHOW_PRODUCT_KEY, "") or "").strip())


def render_image_slideshow(product: dict, *, media_service, view: str = "marketplace") -> None:
    images = [dict(image or {}) for image in (product.get("images", []) or [])]
    if not images:
        st.info("No product images available.")
        if st.button("Back", use_container_width=True, key=f"slideshow_back_empty_{product.get('product_id', '')}"):
            close_slideshow()
            st.rerun()
        return

    active_index = int(st.session_state.get(SLIDESHOW_INDEX_KEY, 0) or 0)
    active_index = max(0, min(active_index, len(images) - 1))
    st.session_state[SLIDESHOW_INDEX_KEY] = active_index
    current_image = images[active_index]
    renderable = media_service.get_renderable_image(current_image)

    st.markdown(f"## {product.get('product_name', product.get('product_id', 'Product'))}")
    st.caption(f"Image {active_index + 1} / {len(images)}")

    if renderable.get("render_mode") == "bytes" and renderable.get("bytes"):
        st.image(renderable["bytes"], use_container_width=True)
    elif renderable.get("render_mode") == "url" and renderable.get("url"):
        st.image(renderable["url"], use_container_width=True)
    else:
        st.warning("Image unavailable.")

    control_cols = st.columns(3)
    if control_cols[0].button("Previous", use_container_width=True, disabled=(active_index <= 0), key=f"slideshow_prev_{product.get('product_id', '')}"):
        st.session_state[SLIDESHOW_INDEX_KEY] = max(0, active_index - 1)
        st.rerun()
    if control_cols[1].button("Back", use_container_width=True, key=f"slideshow_back_{product.get('product_id', '')}"):
        close_slideshow()
        st.rerun()
    if control_cols[2].button("Next", use_container_width=True, disabled=(active_index >= len(images) - 1), key=f"slideshow_next_{product.get('product_id', '')}"):
        st.session_state[SLIDESHOW_INDEX_KEY] = min(len(images) - 1, active_index + 1)
        st.rerun()

    thumb_cols = st.columns(min(len(images), 5))
    for index, image in enumerate(images[:5]):
        with thumb_cols[index]:
            if st.button(
                f"{index + 1}",
                use_container_width=True,
                type="primary" if index == active_index else "secondary",
                key=f"slideshow_jump_{product.get('product_id', '')}_{index}",
            ):
                st.session_state[SLIDESHOW_INDEX_KEY] = index
                st.rerun()
