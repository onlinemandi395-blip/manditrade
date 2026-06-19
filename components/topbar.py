from __future__ import annotations

from components.html_renderer import render_html


def render_topbar(app_name: str, version: str, role_label: str, language: str, translator) -> None:
    role_text = role_label or "Workspace"
    render_html(
        f"""
        <section class="mt-topbar mt-surface">
          <div class="mt-topbar__meta">
            <div class="mt-eyebrow">MandiTrade Control Surface</div>
            <h1>{app_name}</h1>
            <p>Operate catalog, orders, payments, and logistics from one shared workspace.</p>
          </div>
          <div class="mt-topbar__context">
            <div class="mt-context-card">
              <span>Current Role</span>
              <strong>{role_text}</strong>
            </div>
            <div class="mt-context-card">
              <span>{translator.t("auth.language")}</span>
              <strong>{language.upper()}</strong>
            </div>
            <div class="mt-context-card">
              <span>Release</span>
              <strong>v{version}</strong>
            </div>
          </div>
          <div class="mt-badge-row">
            <span class="mt-badge">Google Drive runtime</span>
            <span class="mt-badge">JSON-native data</span>
            <span class="mt-badge">Operational workspace</span>
          </div>
        </section>
        """
    )
