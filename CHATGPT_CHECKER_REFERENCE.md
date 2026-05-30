# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the admin onboarding UX and client onboarding CRUD pass.

## Manufacturer Code Generation Status

- Auto-generation is active through [services/governance_service.py](C:/2026/manditrade/manditrade/services/governance_service.py) and [services/manufacturer_onboarding_service.py](C:/2026/manditrade/manditrade/services/manufacturer_onboarding_service.py).
- Current pattern is `MANU001`, `MANU002`, `MANU003`.
- The generator scans existing manufacturers, finds the highest `MANU###` suffix, and allocates the next code.
- Legacy codes such as `MANU-2026-000001` are preserved and do not break the next generated `MANU###` value.
- Duplicate manufacturer codes are blocked at governance registration time.
- Admin create flows no longer rely on manual editable code entry.

## Category Dropdown Status

- Shared product categories are centralized in [services/master_data_service.py](C:/2026/manditrade/manditrade/services/master_data_service.py).
- Manufacturer admin create/edit and manufacturer self-profile now use dropdown multiselects instead of free text.
- The same centralized category source is ready for reuse anywhere else product-category selection is needed.

## Indian State Dropdown Status

- Shared Indian states and union territories are centralized in [services/master_data_service.py](C:/2026/manditrade/manditrade/services/master_data_service.py).
- State selection is now dropdown-based in:
  - [modules/admin/manufacturers.py](C:/2026/manditrade/manditrade/modules/admin/manufacturers.py)
  - [modules/onboarding/manufacturer_onboarding.py](C:/2026/manditrade/manditrade/modules/onboarding/manufacturer_onboarding.py)
  - [modules/profile/dashboard.py](C:/2026/manditrade/manditrade/modules/profile/dashboard.py)
- City remains a separate text input.

## Client Onboarding Navigation Status

- Manufacturer navigation now includes `Clients` in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py).
- Client onboarding is no longer buried in dashboard-only flow for manufacturer management.
- Route wiring remains in [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py).

## Client CRUD Status

- Private manufacturer client CRUD is now centered in [services/client_service.py](C:/2026/manditrade/manditrade/services/client_service.py).
- Manufacturer `Clients` page in [modules/clients/dashboard.py](C:/2026/manditrade/manditrade/modules/clients/dashboard.py) now supports:
  - create client
  - view clients
  - edit client
  - deactivate client
  - send Gmail invite
- Client records now include address, delivery contact, delivery instructions, credit limit, ledger flag, status, and invite status.
- Cross-manufacturer privacy is enforced by manufacturer-scoped storage and update/look-up rules.

## Gmail Invite Status

- Invite sending uses the existing Gmail runtime path through [services/client_service.py](C:/2026/manditrade/manditrade/services/client_service.py).
- Successful sends mark `invite_status = SENT`.
- Failures are logged when a logging service is present and mark `invite_status = FAILED`.
- No Gmail queue UI was added back.

## Client Sign-In Mapping Status

- Client invite validation and first sign-in activation continue through [services/access_portal_service.py](C:/2026/manditrade/manditrade/services/access_portal_service.py).
- On successful sign-in, the invited client is mapped to the correct manufacturer workspace and activated.
- Invite/profile activation now moves the client state from `INVITED` to `ACTIVE` and `invite_status` to `ACCEPTED`.

## Tests Result

### `python -m pytest tests/ -q`

```text
sssss................................................................... [ 87%]
..........                                                               [100%]
77 passed, 5 skipped in 15.64s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blockers

- Product proposal and approval screens were not updated in this pass to consume the new shared category dropdown data.
- Worker-specific dedicated state dropdown UI was not introduced because the current worker profile uses city/area only.
- Public buyer state dropdown support is updated inside the shared profile page, but there is no separate public-buyer onboarding screen in this repository.
