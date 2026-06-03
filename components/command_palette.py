from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from utils.deep_links import activate_deep_link


def render_command_palette(app_context: dict) -> None:
    service = app_context["operational_search_service"]
    session_state = app_context["session_state_service"]
    available_routes = app_context.get("available_routes", [])
    recent_searches = session_state.get_recent_searches()

    st.markdown("### Command Palette")
    st.caption("Ctrl/Cmd + K")
    render_html(
        """
        <script>
        (function() {
          if (window.__mtCommandPaletteBound) return;
          window.__mtCommandPaletteBound = true;
          document.addEventListener("keydown", function(event) {
            if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === "k") {
              event.preventDefault();
              const input = window.parent.document.querySelector('input[aria-label="Command Palette"]');
              if (input) { input.focus(); input.select(); }
            }
          });
        })();
        </script>
        """
    )
    query = st.text_input("Command Palette", placeholder="Ctrl/Cmd + K: search routes, orders, products, manufacturers...", key="global_command_palette")
    if query.strip():
        session_state.add_recent_search(query)
    route_matches = [
        {"label": route, "entity_type": "route", "entity_id": route, "target": {"route": route, "source_id": route}}
        for route in available_routes
        if not query.strip() or query.strip().lower() in route.lower()
    ][:8]
    search_matches = service.search(app_context, query) if query.strip() else []
    if not query.strip() and recent_searches:
        st.caption("Recent searches")
        for item in recent_searches[:5]:
            st.write(f"- {item}")
    results = route_matches + search_matches
    if not results and query.strip():
        st.info("No commands or records matched the current search.")
        return
    for index, item in enumerate(results[:10]):
        target = item.get("target", {})
        label = str(item.get("label", "Open"))
        meta = f"{item.get('entity_type', 'route')} | {item.get('entity_id', '')}".strip(" |")
        if st.button(f"{label} ({meta})", key=f"command_palette_{index}", use_container_width=True):
            activate_deep_link(target)
            st.rerun()
