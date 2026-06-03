from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.app_bootstrap import default_navigation_section
from components import icon_sidebar
from services.navigation_service import flatten_navigation_groups, get_navigation_groups, navigation_icon_coverage


def test_public_buyer_default_navigation_is_marketplace():
    app_context = {
        "current_user": SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None),
        "session_user": SimpleNamespace(role="public_buyer", email="buyer@example.com", manufacturer_code=None),
        "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
    }

    assert default_navigation_section(app_context) == "Marketplace"


def test_navigation_icon_map_covers_all_live_labels():
    coverage = navigation_icon_coverage()
    labels = {item for role_groups in [get_navigation_groups("platform_admin"), get_navigation_groups("manufacturer"), get_navigation_groups("mahajan"), get_navigation_groups("public_buyer"), get_navigation_groups("worker")] for item in flatten_navigation_groups(role_groups)}

    assert labels
    assert all(coverage.get(label) for label in labels)


def test_icon_sidebar_formats_labels_with_icons():
    label = icon_sidebar.format_icon_nav_label("Marketplace")

    assert "Marketplace" in label
    assert label != "Marketplace"


def test_compact_marketplace_and_sidebar_styles_exist():
    tokens = Path("assets/styles/design_tokens.css").read_text(encoding="utf-8")
    theme = Path("assets/styles/manditrade_3d.css").read_text(encoding="utf-8")
    marketplace = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")

    assert "--mt-sidebar-width-compact" in tokens
    assert "--mt-kpi-card-height-compact" in tokens
    assert ".mt-public-product-grid" in theme
    assert "mt-public-product-grid mt-card-grid" in marketplace
