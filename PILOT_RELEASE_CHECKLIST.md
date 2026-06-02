# Pilot Release Checklist

Use this before any controlled live pilot release.

## Environment

- [ ] Google OAuth credentials are configured in `.streamlit/secrets.toml`
- [ ] Google OAuth redirect URI is non-localhost for cloud runtime
- [ ] Streamlit secrets include `admin.admin_email`
- [ ] Streamlit secrets include `security.fernet_key`
- [ ] Streamlit secrets include `security.public_verification_key`
- [ ] `runtime_environment` is set correctly for the target release
- [ ] `notification_mode` is set correctly for the target release
- [ ] `safe_mode` is enabled for staging or production release validation
- [ ] `enable_mock_auth` is disabled
- [ ] `demo_mode` is disabled

## Integrations

- [ ] Drive access is verified from `System Health`
- [ ] Gmail send is verified from `System Health`
- [ ] Admin token is provisioned and verified
- [ ] Backup path under `runtime/backups/` is writable

## Data Hygiene

- [ ] `python scripts/cleanup_test_data.py --dry-run` reviewed
- [ ] Seed or test data with `PILOT_TEST_`, `TEST_`, or `DEMO_` prefixes is cleaned or archived
- [ ] No pilot UI shows debug, mock, or demo wording to normal users
- [ ] No normal-user route exposes old `client` role language

## Validation

- [ ] `python scripts/validate_release_env.py` passes or blockers are explicitly accepted
- [ ] `python scripts/create_release_snapshot.py` created a current release snapshot
- [ ] `python -m pytest tests/ -q` passed
- [ ] `python -m compileall app.py modules services utils components schemas bootstrap scripts` passed
- [ ] `python -c "import app; print('app import ok')"` passed

## Operator Readiness

- [ ] `PILOT_OPERATOR_GUIDE.md` has been reviewed with the pilot operator
- [ ] `DEPLOYMENT.md` matches the current release procedure
- [ ] Ops owner knows how to use `Operations Center`, `Payments`, `Mandi Orders`, and `System Health`
