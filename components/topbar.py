from __future__ import annotations

from components.html_renderer import render_html


def render_topbar(app_name: str, version: str, role_label: str, language: str) -> None:
    render_html(
        f"""
        <section class="mt-topbar">
          <div class="mt-topbar__meta">
            <h1>{app_name}</h1>
            <p>{role_label} • Language: {language.upper()} • Version {version}</p>
          </div>
          <div class="mt-badge-row">
            <span class="mt-badge">JSON runtime</span>
            <span class="mt-badge">Cache loaded</span>
          </div>
        </section>
        """
    )
