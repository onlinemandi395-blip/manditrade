from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from utils.deep_links import activate_deep_link


def render_command_palette(app_context: dict) -> None:
    service = app_context["operational_search_service"]
    session_state = app_context["session_state_service"]
    available_routes = app_context.get("available_routes", [])
    current_user = app_context.get("current_user")
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
    quick_commands = _build_quick_commands(app_context, available_routes, query)
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
    results = quick_commands + route_matches + search_matches
    if not results and query.strip():
        st.info("No commands or records matched the current search.")
        return
    for index, item in enumerate(results[:10]):
        target = item.get("target", {})
        label = str(item.get("label", "Open"))
        meta = f"{item.get('entity_type', 'route')} | {item.get('entity_id', '')}".strip(" |")
        if st.button(f"{label} ({meta})", key=f"command_palette_{index}", use_container_width=True):
            if item.get("command_type") == "recovery_action":
                task = app_context["recovery_action_service"].execute(
                    item.get("command_value", ""),
                    app_context,
                    actor_role=getattr(current_user, "role", ""),
                    actor_id=getattr(current_user, "email", "platform_admin"),
                )
                st.success(f"{label} queued with status {task.get('status', 'UNKNOWN')}.")
            else:
                activate_deep_link(target)
            st.rerun()


def _build_quick_commands(app_context: dict, available_routes: list[str], query: str) -> list[dict]:
    normalized = query.strip().lower()
    current_user = app_context.get("current_user")
    recovery_service = app_context.get("recovery_action_service")
    recovery_actions = recovery_service.list_available_actions(getattr(current_user, "role", "")) if recovery_service else []
    quick_items = [
        {"label": "Create Job", "entity_type": "quick_action", "entity_id": "Jobs", "target": {"route": "Jobs", "source_id": "create_job"}},
        {"label": "Create Product", "entity_type": "quick_action", "entity_id": "Products", "target": {"route": "Products", "source_id": "create_product"}},
        {"label": "Create Raw Material", "entity_type": "quick_action", "entity_id": "Raw Materials", "target": {"route": "Raw Materials", "source_id": "create_raw_material"}},
    ]
    commands = []
    for item in quick_items:
        route = str(item["target"].get("route", ""))
        if route not in available_routes:
            continue
        if normalized and normalized not in item["label"].lower() and normalized not in route.lower():
            continue
        commands.append(item)
    for action in recovery_actions:
        if normalized and normalized not in action["label"].lower():
            continue
        commands.append(
            {
                "label": action["label"],
                "entity_type": "recovery",
                "entity_id": action["action_key"],
                "command_type": "recovery_action",
                "command_value": action["action_key"],
                "target": {},
            }
        )
    return commands[:6]
