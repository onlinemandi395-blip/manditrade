from __future__ import annotations

from pathlib import Path


def test_access_portal_does_not_use_new_tab_google_link():
    content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    assert "target=\"_blank\"" not in content
    assert "st.link_button(\"Continue with Google\"" not in content


def test_public_buyer_login_does_not_use_new_tab_google_link():
    content = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")
    assert "target=\"_blank\"" not in content
    assert "st.link_button(\"Continue with Google as Public Buyer\"" not in content


def test_mock_login_and_manual_google_key_fields_are_not_visible_in_access_surfaces():
    access_content = Path("modules/access/dashboard.py").read_text(encoding="utf-8")
    profile_content = Path("modules/profile/dashboard.py").read_text(encoding="utf-8")
    admin_content = Path("modules/admin/manufacturers.py").read_text(encoding="utf-8")
    onboarding_content = Path("modules/onboarding/manufacturer_onboarding.py").read_text(encoding="utf-8")

    assert "mock login" not in access_content.lower()
    combined = "\n".join([profile_content, admin_content, onboarding_content]).lower()
    assert 'text_input("client id"' not in combined
    assert "text_input('client id'" not in combined
    assert 'text_input("client secret"' not in combined
    assert "text_input('client secret'" not in combined
    assert 'text_input("api key"' not in combined
    assert "text_input('api key'" not in combined


def test_connected_accounts_ui_visibility_rules_are_role_scoped():
    profile_content = Path("modules/profile/dashboard.py").read_text(encoding="utf-8")
    assert "Connected Accounts" in profile_content
    assert "if current_user.role in {\"manufacturer\", \"admin_as_manufacturer\"}" in profile_content
