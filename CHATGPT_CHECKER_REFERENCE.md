# MandiTrade ChatGPT Checker Reference

Generated: 2026-05-23

## Current Runtime Status

- Local OAuth runtime: PASS
- Local Google Drive runtime: PASS
- Local Gmail runtime: PASS
- Long-lived admin token provisioning: PASS
- Long-lived admin runtime token health: PASS
- Notification mode support: IMPLEMENTED
- Deployment environment guardrails: IMPLEMENTED
- Transaction tests: PASS (`22 passed`)
- Integration suite: PASS under gated staging env (`5 passed`)
- Stress runners: PASS in local runner mode (`100/100` procurement and `100/100` delivery)

## Current Recommendation

- Local localhost runtime: GO
- Controlled local staging: GO
- Streamlit Cloud or other non-local pilot rollout: NOT YET

Broader rollout still depends on deployment-target-specific OAuth redirect validation and a non-local runtime pass.

## Verified Runtime Reports

- OAuth runtime report:
  - `runtime/integration_reports/oauth_status_20260523T080454858452.json`
- Drive smoke report:
  - `runtime/integration_reports/drive_smoke_20260523T080441321900.json`
- Gmail smoke report:
  - `runtime/integration_reports/gmail_smoke_20260523T080822821478.json`
- Admin token status report:
  - `runtime/integration_reports/admin_token_status_20260523T084104541027.json`

## What Is Implemented

- Streamlit-first modular app with bootstrap routing and service container wiring
- Google OAuth login flow with session restoration, persisted state handling, and PKCE support
- Google Drive-backed federated storage architecture
- Gmail notification runtime with queue, retry, and dead-letter support
- Centralized JSON mutation authority through `services/safe_drive_write_service.py`
- Transaction coordinators for procurement and order-side workflows
- Rollback, journaling, backups, lock handling, version history, and recovery support
- Health dashboard with runtime diagnostics, recovery tools, metrics, dead-letter visibility, and Google runtime checks
- Long-lived admin refresh token provisioning into `configs/admin_token.enc`

## Key Runtime Services

- App entry:
  - `app.py`
- Bootstrap and routing:
  - `bootstrap/app_bootstrap.py`
  - `bootstrap/service_container.py`
  - `bootstrap/route_registry.py`
- Auth and security:
  - `services/auth_service.py`
  - `services/oauth_callback_service.py`
  - `services/security_service.py`
  - `services/encryption_service.py`
- Google runtime diagnostics:
  - `services/google_runtime_diagnostic_service.py`
- Write safety and recovery:
  - `services/safe_drive_write_service.py`
  - `services/file_lock_service.py`
  - `services/rollback_service.py`
  - `services/startup_recovery_service.py`
- Transaction orchestration:
  - `services/order_transaction_service.py`
  - `services/procurement_transaction_service.py`
  - `services/event_dispatcher.py`
  - `services/id_allocator_service.py`
- Messaging and operations:
  - `services/gmail_service.py`
  - `services/dead_letter_service.py`
  - `services/runtime_metrics_service.py`

## Key UI Surface

- Health and operator tooling:
  - `modules/system/health_dashboard.py`

Admin diagnostics now include:

- `OAuth Status`
- `Test Drive Access`
- `Test Gmail Send`
- `Admin Token Status`

## Important Current Configuration Facts

- Notification mode is now explicit:
  - `mock`
  - `live`
  - `disabled`
- Runtime environment is now explicit:
  - `local`
  - `staging_cloud`
  - `production`
- Cloud runtime rules now enforce:
  - `staging_cloud` cannot use localhost redirect URIs
  - `staging_cloud` cannot use `notification_mode=mock`
  - `staging_cloud` cannot use `demo_mode=true`
  - `staging_cloud` cannot expose mock authentication
  - `production` cannot use localhost redirect URIs
  - `production` cannot use `notification_mode=mock`
  - `production` cannot use `demo_mode=true`
  - `production` cannot expose mock authentication
- Local redirect URI is intentionally:
  - `http://localhost:8501`
- Admin token file is now a real encrypted token:
  - `configs/admin_token.enc`
- Streamlit Cloud secrets template now supports:
  - `[google]`
  - `[admin]`
  - `[security]`
  - `[admin_token] encrypted_token`
- App-side OAuth scopes now include:
  - `openid`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`
  - `https://www.googleapis.com/auth/drive`
  - `https://www.googleapis.com/auth/drive.file`
  - `https://www.googleapis.com/auth/gmail.send`

## Important Guardrails

- Do not reintroduce UI-owned business writes.
- Do not add new JSON write paths outside `services/safe_drive_write_service.py`.
- Keep the current separation:
  - query services read
  - transaction services mutate
  - UI modules call services only
- Do not treat localhost OAuth settings as deployment-ready settings.

## Known Remaining Gaps

- Streamlit Cloud redirect URI and deployment-target OAuth callback validation are still pending.
- Non-local Google runtime should still be revalidated after deployment-target secrets and redirect URI are configured.
- Normal app notifications still require an intentional final selection of `notification_mode`.

## Streamlit Cloud Deployment Checklist

1. Change the OAuth redirect URI from localhost to the deployed Streamlit Cloud callback URI.
2. Update the same redirect URI in Google Cloud Console.
3. Update Streamlit secrets with deployment-target values.
4. If using long-lived admin runtime in cloud, provide `[admin_token].encrypted_token` in Streamlit secrets.
5. Confirm `runtime_environment="staging_cloud"`, `notification_mode="live"`, `demo_mode=false`, `staging_mode=true`, `safe_mode=true`.
6. Deploy or reboot the Streamlit Cloud app.
7. Login as admin with real Google OAuth.
8. Run `OAuth Status`.
9. Run `Test Drive Access`.
10. Run `Test Gmail Send`.
11. Run `Admin Token Status`.
12. Confirm fresh integration reports under `runtime/integration_reports/`.
13. Review `runtime/integration_reports/latest_pilot_status.json`.
14. Only then mark cloud staging GO.

## Best Next Actions

1. Set the non-local deployment config to `runtime_environment="staging_cloud"` and `notification_mode="live"` before rollout.
2. Validate the deployment-target OAuth redirect URI and Google runtime outside localhost.
3. Run Drive, Gmail, OAuth, and admin-token diagnostics again in the deployed environment.
4. Treat cloud staging as NO-GO until `latest_pilot_status.json` shows no blockers.
