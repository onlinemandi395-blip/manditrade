from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from components import detail_drawer, page_hero, platform_shell, status_chip
from components.html_renderer import inject_css
from components.ui_shell import apply_ui_shell


def test_platform_shell_renders_breadcrumbs_and_actions(monkeypatch):
    html_calls: list[str] = []
    hero_calls: list[dict] = []

    monkeypatch.setattr(platform_shell, "render_html", lambda html, height=None: html_calls.append(html))
    monkeypatch.setattr(
        platform_shell,
        "render_page_hero",
        lambda **kwargs: hero_calls.append(kwargs),
    )

    platform_shell.render_platform_shell(
        title="Operations Center",
        subtitle="Unified command view",
        breadcrumbs=["Home", "Operations"],
        primary_actions=["Refresh KPIs"],
        secondary_actions=["Export"],
        role="platform_admin",
        metrics=[("Alerts", "3")],
    )

    assert html_calls
    assert "Home" in html_calls[0]
    assert "Refresh KPIs" in html_calls[0]
    assert hero_calls[0]["title"] == "Operations Center"
    assert hero_calls[0]["role"] == "platform_admin"


def test_page_hero_renders_action_chips(monkeypatch):
    header_calls: list[tuple] = []
    html_calls: list[str] = []

    monkeypatch.setattr(page_hero, "render_page_header", lambda *args, **kwargs: header_calls.append((args, kwargs)))
    monkeypatch.setattr(page_hero, "render_html", lambda html, height=None: html_calls.append(html))

    page_hero.render_page_hero(
        title="Payments",
        subtitle="Settlement control",
        primary_actions=["Verify"],
        secondary_actions=["Export"],
    )

    assert header_calls
    assert html_calls
    assert "Verify" in html_calls[0]
    assert "Export" in html_calls[0]


def test_detail_drawer_renders_panel_and_order_detail(monkeypatch):
    calls: list[tuple[str, dict | str]] = []

    monkeypatch.setattr(detail_drawer, "render_3d_panel", lambda content, title=None, tone=None: calls.append(("panel", {"content": content, "title": title, "tone": tone})))
    monkeypatch.setattr(detail_drawer, "render_order_detail_view", lambda payload: calls.append(("detail", payload)))

    payload = {"order_id": "ORD-1", "status": "PLACED"}
    detail_drawer.render_detail_drawer(payload, title="Order Detail", tone="info")

    assert calls[0][0] == "panel"
    assert calls[0][1]["title"] == "Order Detail"
    assert calls[1] == ("detail", payload)


def test_status_chip_renders_html(monkeypatch):
    html_calls: list[str] = []
    monkeypatch.setattr(status_chip, "render_html", lambda html, height=None: html_calls.append(html))

    chip_html = status_chip.render_status_chip("PAID")
    status_chip.render_labeled_status_chip("Payment", "PAID")

    assert "PAID" in chip_html
    assert html_calls
    assert "Payment" in html_calls[0]


def test_inject_css_avoids_duplicate_markdown(tmp_path: Path, monkeypatch):
    css_file = tmp_path / "tokens.css"
    css_file.write_text(".demo { color: red; }", encoding="utf-8")

    markdown_calls: list[str] = []
    fake_streamlit = SimpleNamespace(markdown=lambda body, unsafe_allow_html=False: markdown_calls.append(body), session_state={})
    monkeypatch.setattr("components.html_renderer.st", fake_streamlit)

    inject_css(css_file)
    inject_css(css_file)

    assert len(markdown_calls) == 1
    assert "_injected_css_paths" in fake_streamlit.session_state


def test_apply_ui_shell_injects_design_tokens_before_main(tmp_path: Path, monkeypatch):
    main_css = tmp_path / "main.css"
    token_css = tmp_path / "tokens.css"
    main_css.write_text(".main { color: blue; }", encoding="utf-8")
    token_css.write_text(".tokens { color: green; }", encoding="utf-8")

    seen_paths: list[Path] = []
    monkeypatch.setattr("components.ui_shell.DESIGN_TOKENS_FILE", token_css)
    monkeypatch.setattr("components.ui_shell.inject_css", lambda path: seen_paths.append(path))

    apply_ui_shell(main_css)

    assert seen_paths == [token_css, main_css]


def test_entity_form_wraps_forms_without_forcing_fixed_height(monkeypatch):
    from components import entity_form

    markdown_calls: list[str] = []
    form_entries: list[str] = []

    class _DummyForm:
        def __enter__(self):
            form_entries.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            form_entries.append("exit")
            return False

    fake_streamlit = SimpleNamespace(
        markdown=lambda body, unsafe_allow_html=False: markdown_calls.append(body),
        form=lambda key: _DummyForm(),
    )
    monkeypatch.setattr("components.entity_form.st", fake_streamlit)

    with entity_form.render_entity_form("demo_form", title="Demo"):
        pass

    assert any("mt-entity-form-wrap" in body for body in markdown_calls)
    assert form_entries == ["enter", "exit"]
