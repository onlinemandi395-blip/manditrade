# MandiTrade Next Architecture

This rewrite is a fresh JSON-driven Streamlit app.

- JSON config drives navigation, modules, dashboards, forms, actions, notifications, and language.
- Session cache loads configs once at runtime and reuses them for rendering.
- Product mapping drives marketplace and commerce grids.
- Orders and notifications are stored in session-backed local JSON collections for now.
- Admin Drive is visible as a runtime status dependency, not a hard requirement for app boot.
