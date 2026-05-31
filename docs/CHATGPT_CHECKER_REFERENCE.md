# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the production UI cleanup pass.

## Production UI Cleanup Status

- Normal user-facing screens have been cleaned up to remove developer-facing runtime and diagnostic copy.
- Pre-login layout now stays focused on:
  - MandiTrade brand
  - short platform explanation
  - sidebar Google login
  - `Dashboard` only navigation
- Technical diagnostics remain available in [modules/system/health_dashboard.py](C:/2026/manditrade/manditrade/modules/system/health_dashboard.py) for SuperUser only.

## Debug Text Removal Status

- User-facing copy was simplified in:
  - [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py)
  - [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)
  - [modules/notifications/dashboard.py](C:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
  - [modules/payments/dashboard.py](C:/2026/manditrade/manditrade/modules/payments/dashboard.py)
  - [modules/profile/dashboard.py](C:/2026/manditrade/manditrade/modules/profile/dashboard.py)
- Production-safe messages now replace technical phrases such as runtime-mode notes, OAuth session wording, and internal access-state labels in normal UI flows.
- A UI config flag now exists in [configs/system_config.json](C:/2026/manditrade/manditrade/configs/system_config.json):
  - `ui.show_debug_text`
  - default: `false`

## System Health Diagnostic Isolation Status

- Technical OAuth, Drive, Gmail, token, failure-report, and integration diagnostics remain isolated to:
  - [modules/system/health_dashboard.py](C:/2026/manditrade/manditrade/modules/system/health_dashboard.py)
- Normal users do not see these diagnostic surfaces in standard dashboards, marketplace, sidebar, or login pages.

## Login And Navigation Status

- Sidebar still shows:
  - `Session`
  - `Continue with Google`
  - `Navigation`
  - `Dashboard`
- `Marketplace` remains hidden before login.
- OAuth behavior is unchanged:
  - sidebar login still uses fresh `build_authorization_url(...)`
  - configured `new_tab` / `same_tab` behavior still works

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blocker

- Same-tab login diagnostics are still preserved for System Health, but `new_tab` remains the safer production default until same-tab is proven stable in deployed validation.
