# Pilot Flow Verification

Generated on 2026-05-30 after end-to-end pilot flow verification.

## Seed Data

Created through [scripts/seed_pilot_flow.py](C:/2026/manditrade/manditrade/scripts/seed_pilot_flow.py) in isolated safe mode.

- SuperAdmin runtime label:
  - `platform_admin`
- Manufacturers:
  - `PILOT_TEST_MANU001`
  - `PILOT_TEST_MANU002`
- Private clients:
  - `PILOT_TEST_CLIENT_0001`
  - `PILOT_TEST_CLIENT_0002`
- Approved products:
  - `PILOT_TEST_PRODUCT_0001`
  - `PILOT_TEST_PRODUCT_0002`
  - `PILOT_TEST_PRODUCT_0003`
- Private client order:
  - `PILOT_TEST_ORDER_0001`
- RFQ:
  - `PILOT_TEST_RFQ_0001`
- RFQ response:
  - `PILOT_TEST_RESPONSE_0001`
- Public marketplace order:
  - `PILOT_TEST_PUBLIC_ORDER_0001`

## Flow Verification

- Private client flow: `PASS`
  - client product view shows client-facing price only
  - client order view hides mandi and marketplace pricing
  - manufacturer confirmation creates private khata entry
  - manufacturer retains own client visibility
  - SuperAdmin-facing artifacts remain aggregate/sanitized
- RFQ flow: `PASS`
  - shortage creates RFQ
  - supplier response requires priced items
  - zero-value response is rejected
  - buyer acceptance creates non-zero mandi khata using `total_price`
  - shared mandi projection remains visible while self inventory stays private
- Public marketplace flow: `PASS`
  - public buyer sees public product with marketplace pricing
  - public buyer nav excludes inventory, RFQ, and ledger
  - public order stays upfront-payment based
  - seller verifies payment successfully
  - public order does not create khata by default
- SuperAdmin supervisor flow: `PASS`
  - dashboard/summary data remains aggregate-only
  - no client names/emails appear in shared summary artifacts
  - manufacturer labels remain visible
  - commission summary route remains available
- Notifications and My Actions: `PASS`
  - buyer payment task appears before payment submission
  - seller verification task appears before payment verification
  - in-app manufacturer and public-buyer notifications are created
  - Gmail runtime path remains message-based
  - no Gmail queue UI was reintroduced in this pass

## Automated Validation

- `python -m pytest tests/ -q`
  - `105 passed, 5 skipped`
- `python -m pytest tests/test_e2e_pilot_flow.py -q`
  - `6 passed`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - `passed`
- `python -c "import app; print('app import ok')"`
  - `app import ok`

## Remaining Issues

- `platform_admin` is still the internal runtime label for SuperAdmin, but this is not blocking the pilot flow.
- SuperAdmin analytics remain table-first operational summaries rather than richer reporting dashboards.
- `import app` still prints expected bare-mode Streamlit warnings outside script runtime; the import itself succeeds.

## Recommendation

`GO` for first real pilot.

Reason:
- private client flow works end to end
- RFQ priced acceptance works end to end
- public marketplace upfront-payment flow works end to end
- SuperAdmin privacy boundary remains intact
- notifications and My Actions are active
- automated verification is green
