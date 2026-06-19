from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


SLIDESHOW_PRODUCT_KEY = "active_slideshow_product_id"
SLIDESHOW_INDEX_KEY = "active_slideshow_index"
SLIDESHOW_RETURN_ROUTE_KEY = "return_route"
SLIDESHOW_CONTEXT_KEY = "active_slideshow_context"
SLIDESHOW_DEBUG_KEYS = "debug_slideshow_keys"

def _register_debug_key(key: str) -> None:
    normalized = str(key or "").strip()
    if not normalized:
        return
    debug_keys = set(st.session_state.get(SLIDESHOW_DEBUG_KEYS, []) or [])
    if normalized in debug_keys:
        raise ValueError(f"Duplicate slideshow key: {normalized}")
    debug_keys.add(normalized)
    st.session_state[SLIDESHOW_DEBUG_KEYS] = sorted(debug_keys)


def build_slideshow_key(product_id: str, context: str, action: str, suffix: str = "") -> str:
    key = "_".join(
        part
        for part in [
            "slideshow",
            str(action or "").strip(),
            str(context or "default").strip(),
            str(product_id or "").strip(),
            str(suffix or "").strip(),
        ]
        if part
    )
    _register_debug_key(key)
    return key


def open_slideshow(*, product_id: str, return_route: str, slideshow_context: str = "") -> None:
    st.session_state[SLIDESHOW_PRODUCT_KEY] = str(product_id or "").strip()
    st.session_state[SLIDESHOW_INDEX_KEY] = 0
    st.session_state[SLIDESHOW_RETURN_ROUTE_KEY] = str(return_route or "").strip()
    st.session_state[SLIDESHOW_CONTEXT_KEY] = str(slideshow_context or "").strip()
    st.session_state[SLIDESHOW_DEBUG_KEYS] = []


def close_slideshow() -> None:
    st.session_state.pop(SLIDESHOW_PRODUCT_KEY, None)
    st.session_state.pop(SLIDESHOW_INDEX_KEY, None)
    st.session_state.pop(SLIDESHOW_CONTEXT_KEY, None)
    st.session_state.pop(SLIDESHOW_DEBUG_KEYS, None)


def is_slideshow_active() -> bool:
    return bool(str(st.session_state.get(SLIDESHOW_PRODUCT_KEY, "") or "").strip())


def _resolve_gallery_config(ui_config: dict | None) -> dict:
    config = dict((((ui_config or {}).get("product_gallery") or {}).get("slideshow") or {}))
    return {
        "show_thumbnail_strip": bool(config.get("show_thumbnail_strip", True)),
        "max_thumbnail_count": max(1, int(config.get("max_thumbnail_count", 6) or 6)),
        "show_image_counter": bool(config.get("show_image_counter", True)),
        "show_image_file_name": bool(config.get("show_image_file_name", True)),
    }


def render_image_slideshow(
    product: dict,
    *,
    media_service,
    view: str = "marketplace",
    translator=None,
    ui_config: dict | None = None,
    slideshow_context: str = "",
) -> None:
    t = translator.t if translator else (lambda key: key)
    gallery_config = _resolve_gallery_config(ui_config)
    product_id = str(product.get("product_id", "") or "").strip()
    context = str(slideshow_context or "default").strip()
    images = [dict(image or {}) for image in (product.get("images", []) or [])]
    if not images:
        st.info(t("ui.no_product_images_available"))
        if st.button(t("ui.back"), use_container_width=True, key=build_slideshow_key(product_id, context, "back", "empty")):
            close_slideshow()
            st.rerun()
        return

    active_index = int(st.session_state.get(SLIDESHOW_INDEX_KEY, 0) or 0)
    active_index = max(0, min(active_index, len(images) - 1))
    st.session_state[SLIDESHOW_INDEX_KEY] = active_index
    current_image = images[active_index]
    renderable = media_service.get_renderable_image(current_image)

    st.markdown(f"## {product.get('product_name', product.get('product_id', t('ui.product')))}")
    if gallery_config["show_image_counter"]:
        st.caption(f"{t('ui.image')} {active_index + 1} / {len(images)}")

    image_col_spec = [1.2, 4.6] if gallery_config["show_thumbnail_strip"] and len(images) > 1 else [1]
    layout_cols = st.columns(image_col_spec)
    thumb_limit = min(len(images), gallery_config["max_thumbnail_count"])
    if len(layout_cols) > 1:
        with layout_cols[0]:
            st.markdown(f"##### {t('ui.gallery')}")
            for index, image in enumerate(images[:thumb_limit]):
                preview = media_service.get_renderable_image(image)
                if preview.get("render_mode") == "bytes" and preview.get("bytes"):
                    st.image(preview["bytes"], use_container_width=True)
                elif preview.get("render_mode") == "url" and preview.get("url"):
                    st.image(preview["url"], use_container_width=True)
                else:
                    render_template("slideshow_thumb_placeholder.html", label="No Image")
                if st.button(
                    f"{t('ui.image')} {index + 1}",
                    use_container_width=True,
                    type="primary" if index == active_index else "secondary",
                    key=build_slideshow_key(product_id, context, "jump", str(index)),
                ):
                    st.session_state[SLIDESHOW_INDEX_KEY] = index
                    st.rerun()
    hero_col = layout_cols[-1]
    with hero_col:
        if renderable.get("render_mode") == "bytes" and renderable.get("bytes"):
            st.image(renderable["bytes"], use_container_width=True)
        elif renderable.get("render_mode") == "url" and renderable.get("url"):
            st.image(renderable["url"], use_container_width=True)
        else:
            st.warning(t("ui.image_unavailable"))
        if gallery_config["show_image_file_name"]:
            st.caption(str(current_image.get("file_name", "") or current_image.get("image_id", "")))

    control_cols = st.columns(3)
    if control_cols[0].button(t("ui.previous"), use_container_width=True, disabled=(active_index <= 0), key=build_slideshow_key(product_id, context, "prev")):
        st.session_state[SLIDESHOW_INDEX_KEY] = max(0, active_index - 1)
        st.rerun()
    if control_cols[1].button(t("ui.back_to_products"), use_container_width=True, key=build_slideshow_key(product_id, context, "back")):
        close_slideshow()
        st.rerun()
    if control_cols[2].button(t("ui.next"), use_container_width=True, disabled=(active_index >= len(images) - 1), key=build_slideshow_key(product_id, context, "next")):
        st.session_state[SLIDESHOW_INDEX_KEY] = min(len(images) - 1, active_index + 1)
        st.rerun()
