from __future__ import annotations

from pathlib import Path

from services.navigation_service import ROLE_NAVIGATION_MAP, flatten_navigation_groups


def test_live_navigation_contains_no_client_sections():
    for role, groups in ROLE_NAVIGATION_MAP.items():
        if role in {"unauthenticated", "pending_user"}:
            continue
        sections = flatten_navigation_groups(groups)
        combined = " | ".join(sections)
        assert "Client" not in combined
        assert "Clients" not in combined
        assert "Client Orders" not in combined


def test_live_ui_files_hide_client_role_language():
    files = [
        Path("modules/access/dashboard.py"),
        Path("modules/admin/product_approvals.py"),
        Path("modules/admin/commission_summary.py"),
        Path("modules/agreements/dashboard.py"),
        Path("modules/analytics/dashboard.py"),
        Path("modules/inventory/management.py"),
        Path("modules/ledger/dashboard.py"),
        Path("modules/mahajan/dashboard.py"),
        Path("modules/manufacturer/dashboard.py"),
        Path("modules/marketplace/dashboard.py"),
        Path("modules/pricing/dashboard.py"),
        Path("modules/procurement/dashboard.py"),
        Path("modules/rfq/dashboard.py"),
        Path("modules/workers/dashboard.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for forbidden in [
        "Client Orders",
        "Private Client",
        "Private client",
        "Private Buyer",
        "Client Ledger",
        "Approved Client Price",
        "Client Price",
    ]:
        assert forbidden not in combined


def test_client_price_remains_compatibility_only_not_ui_label():
    pricing_content = Path("modules/pricing/dashboard.py").read_text(encoding="utf-8")
    approvals_content = Path("modules/admin/product_approvals.py").read_text(encoding="utf-8")
    products_content = Path("modules/products/dashboard.py").read_text(encoding="utf-8")

    assert "B2B Price" in pricing_content
    assert "Approved B2B Price" in approvals_content
    assert "Suggested B2B Price" in products_content
    assert "Client Price" not in pricing_content
    assert "Approved Client Price" not in approvals_content


def test_checker_reference_matches_final_five_role_model():
    content = Path("docs/CHATGPT_CHECKER_REFERENCE.md").read_text(encoding="utf-8")
    assert "platform_admin" in content
    assert "manufacturer" in content
    assert "mahajan" in content
    assert "public_buyer" in content
    assert "worker" in content
    assert "Removed from live RBAC" in content


def test_key_docs_do_not_advertise_removed_client_architecture():
    files = [
        Path("docs/CHATGPT_CHECKER_REFERENCE.md"),
        Path("docs/PILOT_FLOW_VERIFICATION.md"),
        Path("docs/CODEX_TO_CHATGPT_GUIDANCE_REQUEST.md"),
        Path("docs/POST_PILOT_PRIORITY_FRAMEWORK.md"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)
    assert "private client flow" not in combined
    assert "client onboarding" not in combined
    assert "manufacturer clients" not in combined
    assert "client proposal order" not in combined
