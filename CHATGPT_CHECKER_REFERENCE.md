# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the consent-based Google runtime and same-tab authentication pass.

## Consent-Based Manufacturer Drive/Gmail Model

- Platform OAuth remains centralized under the platform Google OAuth app.
- Login identity for all users continues through the same platform OAuth client.
- Manufacturer connected-account consent now routes through [services/connected_accounts_service.py](C:/2026/manditrade/manditrade/services/connected_accounts_service.py).
- Manufacturer Drive connect uses OAuth consent with `drive.file`.
- Manufacturer Gmail connect is available as consent-based plumbing, while platform-sender fallback remains the default operational mode when no manufacturer Gmail token is connected.
- Clients and public buyers continue to use Google identity login only and do not receive Drive/Gmail consent prompts.

## Manual API Key Removal Status

- No manufacturer-facing profile/onboarding/admin UI asks for `client_id`, `client_secret`, or API keys.
- Manufacturer connection handling is consent-based only.
- Manufacturer profile now explicitly explains that raw credentials are not exposed.

## Same-Tab Google Sign-In Status

- Same-tab Google login links are now rendered from:
  - [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py)
  - [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)
- These flows now use HTML anchors with `target="_self"` via [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py).
- `st.link_button(...)` is no longer used for the Google login entry points covered in this pass.

## Connected Accounts UI Status

- Manufacturer and admin-as-manufacturer Connected Accounts UI is now shown inside [modules/profile/dashboard.py](C:/2026/manditrade/manditrade/modules/profile/dashboard.py).
- Current Connected Accounts section shows:
  - Drive connected: yes/no
  - Drive email
  - Last validation
  - Gmail mode: own/platform
  - same-tab `Connect Google Drive`
  - same-tab `Connect Gmail`
  - disconnect controls
- Clients, public buyers, and workers do not get Connected Accounts controls because their profile routes do not render this section.

## Scope Separation Status

- OAuth flow separation now lives in [services/oauth_callback_service.py](C:/2026/manditrade/manditrade/services/oauth_callback_service.py).
- Separate flow types are tracked for:
  - `login_oauth`
  - `manufacturer_drive_connect`
  - `manufacturer_gmail_connect`
  - `admin_token_provision`
- Login scopes are restricted to:
  - `openid`
  - `userinfo.email`
  - `userinfo.profile`
- Manufacturer Drive connect scopes are restricted to:
  - `https://www.googleapis.com/auth/drive.file`
- Manufacturer Gmail connect scopes are restricted to:
  - `https://www.googleapis.com/auth/gmail.send`

## Private Token Metadata Status

- Connected-account metadata is stored under manufacturer private zone in `connected_accounts.json`.
- Encrypted refresh tokens are stored under manufacturer private-zone `tokens/`.
- Shared/public zones do not receive connected-account metadata or token files.

## Diagnostics Status

- Manufacturer profile shows Drive/Gmail connection summary.
- Admin System Health now shows Connected Accounts summary counts through [modules/system/health_dashboard.py](C:/2026/manditrade/manditrade/modules/system/health_dashboard.py):
  - connected manufacturers count
  - disconnected manufacturers count
  - failed token validations
- Detailed token values are not exposed in the UI.

## Tests Result

### `python -m pytest tests/ -q`

```text
sssss................................................................... [ 79%]
...................                                                      [100%]
86 passed, 5 skipped in 15.77s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blocker

- Manufacturer Gmail consent plumbing and status UI are in place, but outbound message sending still defaults to the platform sender runtime unless the downstream Gmail send path is explicitly switched to manufacturer-owned credentials in a later pass.
