from __future__ import annotations

from pathlib import Path


def test_ui_consistency_audit_exists_and_classifies_modules():
    content = Path("docs/UI_CONSISTENCY_AUDIT.md").read_text(encoding="utf-8")

    assert "MIGRATED" in content
    assert "PARTIAL" in content
    assert "LEGACY_UI" in content
    assert "modules/marketplace/dashboard.py" in content
    assert "modules/raw_materials/dashboard.py" in content


def test_access_page_uses_platform_shell_without_private_navigation_copy():
    content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")

    assert "render_platform_shell(" in content
    assert "Use sidebar sign-in" in content
    assert "Marketplace nav" not in content


def test_second_wave_pages_reference_shared_components():
    marketplace = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")
    raw_materials = Path("modules/raw_materials/dashboard.py").read_text(encoding="utf-8")
    suta_mandi = Path("modules/suta_mandi/dashboard.py").read_text(encoding="utf-8")
    logistics = Path("modules/logistics/dashboard.py").read_text(encoding="utf-8")

    assert "render_platform_shell(" in marketplace
    assert "render_platform_shell(" in raw_materials
    assert "render_data_grid(" in raw_materials
    assert "render_platform_shell(" in suta_mandi
    assert "render_data_grid(" in suta_mandi
    assert "render_platform_shell(" in logistics
    assert "render_data_grid(" in logistics
