# Pilot Flow Verification

Generated on 2026-06-02 after the final terminology-hardening pass.

## Final Pilot Model

- Roles:
  - `platform_admin`
  - `manufacturer`
  - `mahajan`
  - `public_buyer`
  - `worker`
- Networks:
  - `Marketplace`
  - `MandiPlace`
  - `Raw Materials`
  - `Suta Mandi`

## Verified Flow Areas

- Marketplace flow: `PASS`
  - public buyer sees marketplace pricing only
  - public buyer navigation excludes inventory, ledger, and mandi routes
  - public order remains upfront-payment based
  - seller verification works
- MandiPlace flow: `PASS`
  - manufacturer order lane remains separate from Marketplace
  - B2B pricing stays manufacturer-facing
  - mandi procurement routing still works
- Raw-material supply flow: `PASS`
  - admin routes supply requests
  - mahajan quote and dispatch flow works
  - supply ledger and mandi ledger remain separate
- SuperUser supervision: `PASS`
  - aggregate-only summaries remain intact
  - no removed client-role navigation is exposed

## Automated Validation

- `python -m pytest tests/ -q`
  - `165 passed, 5 skipped`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - `passed`
- `python -c "import app; print('app import ok')"`
  - `app import ok`

## Notes

- Historical client-era pilot wording is retired from the live product description.
- Compatibility storage fields may still use legacy names internally, but the pilot model is now documented only in final 5-role / 3-network terms.
