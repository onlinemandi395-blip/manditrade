# Deployment

## Streamlit Cloud Secrets

Configure these sections in `.streamlit/secrets.toml`:

- `[google]`
  - `client_id`
  - `client_secret`
  - `redirect_uri`
- `[admin]`
  - `admin_email`
- `[security]`
  - `fernet_key`
  - `public_verification_key`

## Google OAuth Redirect URI

- `local`: `http://localhost:8501`
- `staging_cloud` or `production`: use the real deployed Streamlit URL

Cloud release validation should never use a localhost redirect URI.

## Local vs Cloud Config

- `runtime_environment=local`
  - local redirect URI is allowed
  - local diagnostics are acceptable
- `runtime_environment=staging_cloud`
  - no localhost redirect
  - `notification_mode=live`
  - `enable_mock_auth=false`
  - `demo_mode=false`
- `runtime_environment=production`
  - same restrictions as staging, with stricter operator discipline

## Validation Script

Run:

```bash
python scripts/validate_release_env.py
```

The script writes JSON reports to:

```text
runtime/release_reports/
```

## Test Data Cleanup

Dry run:

```bash
python scripts/cleanup_test_data.py --dry-run
```

Execute:

```bash
python scripts/cleanup_test_data.py --execute
```

Archived originals are stored under:

```text
runtime/release_cleanup/
```

## Release Snapshot

Run:

```bash
python scripts/create_release_snapshot.py
```

Snapshots are stored under:

```text
runtime/release_snapshots/
```

## System Health Verification

Before release, check `System Health` for:

- startup blockers
- OAuth warnings
- Drive write health
- Gmail mode
- recovery tools
- search index rebuild
- KPI and alert regeneration

## Release Gate

```bash
python scripts/validate_release_env.py
python scripts/cleanup_test_data.py --dry-run
python scripts/create_release_snapshot.py
python -m pytest tests/ -q
python -m compileall app.py modules services utils components schemas bootstrap scripts
python -c "import app; print('app import ok')"
```
