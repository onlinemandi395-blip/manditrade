# Pilot Operator Guide

This guide is for the person monitoring the live pilot day to day.

## Daily Checks

Open these areas in order:

1. `Operations Center`
2. `Alerts`
3. `Payments`
4. `Mandi Orders`
5. `Supply Orders`
6. `Marketplace Orders`
7. `System Health`

## Daily Routine

1. Check for unresolved `CRITICAL` alerts first.
2. Review overdue payments and delayed dispatches.
3. Confirm active mandi orders are moving between quote, price, confirmation, and dispatch states.
4. Verify marketplace orders are not stuck at payment or delivery stages.
5. Review `System Health` for Drive, OAuth, Gmail, and recovery warnings.

## Incident Handling

### OAuth Failure

- Confirm Google OAuth secrets are present.
- Confirm redirect URI matches the deployed host.
- Run `python scripts/validate_release_env.py`.
- Check `runtime/integration_reports/` for the latest diagnostic file.

### Drive Write Failure

- Open `System Health`.
- Check runtime write, backup, and recovery warnings.
- Confirm `runtime/backups/` and `runtime/version_history/` are writable.
- If needed, use recovery utilities to rebuild indexes and refresh snapshots.

### Gmail Failure

- Confirm `notification_mode=live`.
- Confirm Gmail scopes are approved in Google OAuth.
- Check `runtime/logs/` and the latest integration report.

### Payment Mismatch

- Compare the order record with ledger or public payment records.
- Check whether the payment is pending verification or partially settled.
- Escalate any mismatch that affects settlement or dispatch.

### Stuck Order

- Open the order detail view.
- Check the timeline and next action field.
- Confirm the expected role has completed its step.
- If the order is stalled beyond SLA, escalate as `P1` or `P2`.

### Logistics Failure

- Check dispatch details in the order.
- Verify vehicle and delivery metadata were recorded.
- Review related alerts and unresolved notifications.

## Severity Model

- `P0`: Release-blocking outage, data corruption risk, or critical production failure.
- `P1`: High-impact business failure affecting orders, payments, or sign-in.
- `P2`: Important but contained issue with a workaround.
- `P3`: Low-impact bug, copy issue, or non-blocking UI cleanup item.

## Release Gate Commands

```bash
python scripts/validate_release_env.py
python scripts/cleanup_test_data.py --dry-run
python scripts/create_release_snapshot.py
python -m pytest tests/ -q
python -m compileall app.py modules services utils components schemas bootstrap scripts
python -c "import app; print('app import ok')"
```
