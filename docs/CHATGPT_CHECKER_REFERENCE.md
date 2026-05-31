# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the OAuth same-tab RCA and controlled new-tab fallback pass.

## Same-Tab RCA Status

- OAuth RCA is now generated through [services/oauth_callback_service.py](C:/2026/manditrade/manditrade/services/oauth_callback_service.py) into:
  - `runtime/integration_reports/oauth_same_tab_rca_*.json`
- The RCA captures:
  - `client_id_suffix`
  - `redirect_uri`
  - state creation and callback recovery status
  - PKCE creation and callback recovery status
  - whether Streamlit session state survived redirect
  - whether secrets override is active
  - whether oauth config fallback is active
  - failure reason
  - recommended navigation mode
- Current safe conclusion is:
  - same-tab is diagnosable
  - persistent runtime state storage exists
  - default login mode should remain `new_tab` until same-tab proves reliable in deployed Streamlit runtime

## Chosen Login Mode Status

- Login navigation mode is now configurable in [configs/system_config.json](C:/2026/manditrade/manditrade/configs/system_config.json):
  - `same_tab`
  - `new_tab`
- Current default is:
  - `new_tab`
- Sidebar and top-header login rendering now use the configured mode through:
  - [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py)

## Sidebar-Only Login Status

- Before login, sidebar still shows:
  - `Session`
  - `Continue with Google`
  - `Navigation`
  - `Dashboard`
- Google login now appears only in the sidebar session area.
- The main page/header no longer renders a duplicate login button.
- `Marketplace` remains hidden before login.
- `Access` is not shown as a navigation item.
- The Google login CTA is still built from fresh `build_authorization_url(...)` output and is never hardcoded.

## State / PKCE Persistence Status

- OAuth state and PKCE verifier are persisted outside volatile session state through:
  - [services/oauth_callback_service.py](C:/2026/manditrade/manditrade/services/oauth_callback_service.py)
  - `runtime/oauth_states.json`
- Callback validation can recover from persisted runtime state even if same-tab or cross-tab browser behavior drops Streamlit session state.
- System Health now exposes:
  - login navigation mode
  - last OAuth failure reason
  - same-tab RCA snapshot
  - state persistence mode
  - redirect URI
  - client ID suffix
  - secrets override active
  - fallback active

## Public Buyer Fallback Status

- Unknown Google users still default into `public_buyer` through [services/access_portal_service.py](C:/2026/manditrade/manditrade/services/access_portal_service.py).
- `pending_user` is not used for normal unknown Google users.
- `pending_user` remains reserved for blocked accounts or when public auto-onboarding is disabled.

## Post-Login RBAC Status

- Post-login RBAC logic is unchanged by this pass.
- Successful OAuth callback still initializes the correct runtime session and lands the user in the correct role-aware workspace.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blocker

- Same-tab login is now better diagnosed, but deployed Streamlit browser/runtime behavior may still drop volatile session state during redirect in some cases. `new_tab` remains the safer default until same-tab is proven stable in production-like validation.
