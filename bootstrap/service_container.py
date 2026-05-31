from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from services.action_center_service import ActionCenterService
from services.access_portal_service import AccessPortalService
from services.audit_service import AuditService
from services.auth_service import AuthService
from services.bootstrap_service import BootstrapService
from services.cache_service import CacheService
from services.catalog_service import CatalogService
from services.client_service import ClientService
from services.config_service import ConfigService
from services.connected_accounts_service import ConnectedAccountsService
from services.delivery_service import DeliveryService
from services.dead_letter_service import DeadLetterService
from services.domain_paths_service import DomainPathsService
from services.drive_service import DriveService
from services.dual_inventory_service import DualInventoryService
from services.encryption_service import EncryptionService
from services.event_dispatcher import EventDispatcher
from services.file_lock_service import FileLockService
from services.gmail_service import GmailService
from services.google_runtime_diagnostic_service import GoogleRuntimeDiagnosticService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.job_service import JobService
from services.ledger_reminder_service import LedgerReminderService
from services.ledger_service import LedgerService
from services.logging_service import LoggingService
from services.manufacturer_onboarding_service import ManufacturerOnboardingService
from services.notification_center_service import NotificationCenterService
from services.oauth_callback_service import OAuthCallbackService
from services.order_state_service import OrderStateService
from services.order_transaction_service import OrderTransactionService
from services.procurement_transaction_service import ProcurementTransactionService
from services.product_catalog_service import ProductCatalogService
from services.public_buyer_service import PublicBuyerService
from services.public_cart_service import PublicCartService
from services.public_order_service import PublicOrderService
from services.pricing_service import PricingService
from services.query.inventory_query_service import InventoryQueryService
from services.query.order_query_service import OrderQueryService
from services.query.procurement_query_service import ProcurementQueryService
from services.rollback_service import RollbackService
from services.runtime_metrics_service import RuntimeMetricsService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.security_service import SecurityService
from services.startup_recovery_service import StartupRecoveryService
from services.token_rotation_service import TokenRotationService
from services.trade_confirmation_service import TradeConfirmationService
from services.worker_service import WorkerService
from utils.config_loader import load_config
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR, RUNTIME_BACKUPS_DIR, RUNTIME_DEAD_LETTER_DIR, RUNTIME_LOGS_DIR, RUNTIME_METRICS_DIR, RUNTIME_RECOVERY_DIR, RUNTIME_TOKENS_DIR, RUNTIME_VERSION_HISTORY_DIR


def build_app_context() -> dict:
    config_service = ConfigService()
    config_issues = config_service.validate()
    system_config = load_config("system_config.json")
    oauth_config = load_config("oauth_config.json")
    feature_flags = load_config("feature_flags.json")
    subscription_plans = load_config("subscription_plans.json")
    system_config.setdefault("ledger_reminders", {"enabled": True, "upcoming_days_before": 3, "final_reminder_after_days": 15, "max_reminders_per_due": 4})
    system_config.setdefault(
        "public_payment",
        {
            "mode": "UPI_MANUAL",
            "upi_id": "",
            "payee_name": "",
            "instructions": "Pay full amount upfront and enter UTR.",
        },
    )
    system_config.setdefault(
        "commission",
        {
            "admin_profit_share_percent": 50,
            "manufacturer_profit_share_percent": 50,
            "platform_fee_on_admin_commission": {"basic": 10, "premium": 5, "premium_plus": 1},
        },
    )

    bootstrap_service = BootstrapService(BASE_DIR)
    bootstrap_service.ensure_runtime_structure()
    drive_service = DriveService(
        local_root=MANUFACTURERS_DIR,
        manufacturer_root_prefix=system_config["storage"]["manufacturer_root_prefix"],
        shared_zone_name=system_config["storage"]["shared_zone_name"],
        private_zone_name=system_config["storage"]["private_zone_name"],
        use_drive_api=system_config["storage"]["use_drive_api"],
        safe_drive_write_service=None,
        logging_service=None,
        runtime_metrics_service=None,
    )
    oauth_secrets_override_active = False
    if "google" in st.secrets and oauth_config.get("streamlit_cloud", {}).get("allow_secret_override", True):
        google_secret_overrides = dict(st.secrets["google"])
        oauth_config["google_oauth"]["client_id"] = google_secret_overrides.get("client_id", oauth_config["google_oauth"]["client_id"])
        oauth_config["google_oauth"]["client_secret"] = google_secret_overrides.get("client_secret", oauth_config["google_oauth"]["client_secret"])
        oauth_config["google_oauth"]["redirect_uri"] = google_secret_overrides.get("redirect_uri", oauth_config["google_oauth"]["redirect_uri"])
        oauth_secrets_override_active = bool(
            google_secret_overrides.get("client_id")
            and google_secret_overrides.get("client_secret")
            and google_secret_overrides.get("redirect_uri")
        )
    oauth_config_fallback_active = not oauth_secrets_override_active

    auth_service = AuthService(oauth_config=oauth_config, enable_mock_auth=system_config["security"]["enable_mock_auth"])
    security_secret_overrides = dict(st.secrets["security"]) if "security" in st.secrets else {}
    encryption_service = EncryptionService(secret_seed=system_config["app"]["name"], fernet_key=security_secret_overrides.get("fernet_key"))
    file_lock_service = FileLockService()
    security_service = SecurityService(
        encryption_service=encryption_service,
        auth_service=auth_service,
        admin_token_file=BASE_DIR / system_config["security"]["admin_token_file"],
        manufacturer_token_dir=BASE_DIR / system_config["security"]["manufacturer_token_dir"],
        runtime_tokens_dir=BASE_DIR / system_config["security"]["runtime_tokens_dir"],
        require_verification_for_admin_runtime=system_config["security"]["require_verification_for_admin_runtime"],
    )
    audit_service = AuditService(log_path=APP_RUNTIME_DIR / "audit" / "audit.log")
    logging_service = LoggingService(logs_dir=RUNTIME_LOGS_DIR)
    schema_validation_service = SchemaValidationService()
    id_allocator_service = IdAllocatorService(APP_RUNTIME_DIR / "id_counters.json", file_lock_service)
    dead_letter_service = DeadLetterService(RUNTIME_DEAD_LETTER_DIR, id_allocator_service=id_allocator_service)
    runtime_metrics_service = RuntimeMetricsService(RUNTIME_METRICS_DIR)
    drive_service.logging_service = logging_service
    drive_service.runtime_metrics_service = runtime_metrics_service
    gmail_service = GmailService(
        sender_email=system_config["notifications"]["admin_sender_email"],
        use_gmail_api=system_config["notifications"]["use_gmail_api"],
        queue_path=None,
        safe_drive_write_service=None,
        dead_letter_service=dead_letter_service,
        logging_service=logging_service,
        runtime_metrics_service=runtime_metrics_service,
        notification_mode=system_config["notifications"].get("notification_mode", "mock"),
        auth_service=auth_service,
        security_service=security_service,
    )
    token_rotation_service = TokenRotationService(auth_service=auth_service)
    cache_service = CacheService()
    event_dispatcher = EventDispatcher(APP_RUNTIME_DIR / "events", id_allocator_service=id_allocator_service, dead_letter_service=dead_letter_service, logging_service=logging_service, runtime_metrics_service=runtime_metrics_service)
    safe_drive_write_service = SafeDriveWriteService(
        json_service=drive_service.json_service,
        file_lock_service=file_lock_service,
        schema_validation_service=schema_validation_service,
        backups_root=RUNTIME_BACKUPS_DIR,
        logging_service=logging_service,
        version_history_root=RUNTIME_VERSION_HISTORY_DIR,
    )
    rollback_service = RollbackService(safe_drive_write_service=safe_drive_write_service, logging_service=logging_service)
    drive_service.safe_drive_write_service = safe_drive_write_service
    gmail_service.safe_drive_write_service = safe_drive_write_service
    governance_service = GovernanceService(governance_root=GOVERNANCE_DIR, safe_drive_write_service=safe_drive_write_service)
    governance_service.ensure_files()
    oauth_callback_service = OAuthCallbackService(
        auth_service=auth_service,
        security_service=security_service,
        state_store_path=APP_RUNTIME_DIR / "oauth_states.json",
        runtime_reports_root=APP_RUNTIME_DIR / "integration_reports",
        runtime_environment=system_config["app"].get("runtime_environment", "local"),
    )
    client_service = ClientService(
        drive_service=drive_service,
        gmail_service=gmail_service,
        encryption_service=encryption_service,
        safe_drive_write_service=safe_drive_write_service,
        id_allocator_service=id_allocator_service,
        logging_service=logging_service,
    )
    connected_accounts_service = ConnectedAccountsService(
        drive_service=drive_service,
        security_service=security_service,
        auth_service=auth_service,
        oauth_callback_service=oauth_callback_service,
        json_service=drive_service.json_service,
        safe_drive_write_service=safe_drive_write_service,
    )
    catalog_service = CatalogService(governance_root=GOVERNANCE_DIR)
    manufacturer_onboarding_service = ManufacturerOnboardingService(
        drive_service=drive_service,
        governance_service=governance_service,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
    )
    domain_paths_service = DomainPathsService(drive_service=drive_service)
    dual_inventory_service = DualInventoryService(safe_drive_write_service=safe_drive_write_service, json_service=drive_service.json_service, domain_paths_service=domain_paths_service)
    trade_confirmation_service = TradeConfirmationService(safe_drive_write_service=safe_drive_write_service, json_service=drive_service.json_service, id_allocator_service=id_allocator_service, domain_paths_service=domain_paths_service)
    ledger_service = LedgerService(safe_drive_write_service=safe_drive_write_service, json_service=drive_service.json_service, id_allocator_service=id_allocator_service, domain_paths_service=domain_paths_service)
    public_buyers_root = BASE_DIR / "data" / "public_buyers"
    public_orders_root = BASE_DIR / "data" / "public_orders"
    public_payments_root = BASE_DIR / "data" / "public_payments"
    notification_center_service = NotificationCenterService(
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
        domain_paths_service=domain_paths_service,
        public_buyers_root=public_buyers_root,
    )
    pricing_service = PricingService(system_config.get("commission", {}))
    product_catalog_service = ProductCatalogService(
        governance_service=governance_service,
        id_allocator_service=id_allocator_service,
        notification_center_service=notification_center_service,
        gmail_service=gmail_service,
        admin_email=security_service.get_admin_email(),
        pricing_service=pricing_service,
    )
    public_buyer_service = PublicBuyerService(
        public_buyers_root=public_buyers_root,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
    )
    public_cart_service = PublicCartService(
        public_buyer_service=public_buyer_service,
        product_catalog_service=product_catalog_service,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
    )
    public_order_service = PublicOrderService(
        public_orders_root=public_orders_root,
        public_payments_root=public_payments_root,
        public_buyer_service=public_buyer_service,
        public_cart_service=public_cart_service,
        product_catalog_service=product_catalog_service,
        dual_inventory_service=dual_inventory_service,
        notification_center_service=notification_center_service,
        gmail_service=gmail_service,
        governance_service=governance_service,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
        pricing_service=pricing_service,
        config=system_config.get("public_payment", {}),
    )
    worker_service = WorkerService(
        governance_root=GOVERNANCE_DIR,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
    )
    job_service = JobService(
        governance_root=GOVERNANCE_DIR,
        safe_drive_write_service=safe_drive_write_service,
        json_service=drive_service.json_service,
        id_allocator_service=id_allocator_service,
        notification_center_service=notification_center_service,
        ledger_service=ledger_service,
        gmail_service=gmail_service,
    )
    access_portal_service = AccessPortalService(
        governance_root=GOVERNANCE_DIR,
        safe_drive_write_service=safe_drive_write_service,
        governance_service=governance_service,
        client_service=client_service,
        worker_service=worker_service,
        public_buyer_service=public_buyer_service,
        drive_service=drive_service,
        security_service=security_service,
        json_service=drive_service.json_service,
    )
    order_state_service = OrderStateService(audit_service=audit_service)
    delivery_service = DeliveryService(gmail_service=gmail_service, audit_service=audit_service, id_allocator_service=id_allocator_service)
    procurement_transaction_service = ProcurementTransactionService(
        drive_service=drive_service,
        safe_drive_write_service=safe_drive_write_service,
        rollback_service=rollback_service,
        gmail_service=gmail_service,
        audit_service=audit_service,
        logging_service=logging_service,
        transactions_root=APP_RUNTIME_DIR / "transactions",
        event_dispatcher=event_dispatcher,
        id_allocator_service=id_allocator_service,
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_center_service,
        domain_paths_service=domain_paths_service,
    )
    order_transaction_service = OrderTransactionService(
        drive_service=drive_service,
        safe_drive_write_service=safe_drive_write_service,
        rollback_service=rollback_service,
        order_state_service=order_state_service,
        delivery_service=delivery_service,
        gmail_service=gmail_service,
        audit_service=audit_service,
        logging_service=logging_service,
        event_dispatcher=event_dispatcher,
        transactions_root=APP_RUNTIME_DIR / "order_transactions",
        id_allocator_service=id_allocator_service,
        dual_inventory_service=dual_inventory_service,
        trade_confirmation_service=trade_confirmation_service,
        ledger_service=ledger_service,
        notification_center_service=notification_center_service,
        domain_paths_service=domain_paths_service,
        pricing_service=pricing_service,
        procurement_transaction_service=procurement_transaction_service,
    )
    startup_recovery_service = StartupRecoveryService(procurement_transaction_service=procurement_transaction_service, order_transaction_service=order_transaction_service, file_lock_service=file_lock_service, recovery_root=RUNTIME_RECOVERY_DIR, runtime_metrics_service=runtime_metrics_service)
    ledger_reminder_service = LedgerReminderService(gmail_service=gmail_service, ledger_service=ledger_service, safe_drive_write_service=safe_drive_write_service, domain_paths_service=domain_paths_service, json_service=drive_service.json_service, config=system_config)
    action_center_service = ActionCenterService(
        governance_service=governance_service,
        gmail_service=gmail_service,
        notification_center_service=notification_center_service,
        ledger_service=ledger_service,
        order_query_service=OrderQueryService(drive_service=drive_service, json_service=drive_service.json_service, domain_paths_service=domain_paths_service),
        procurement_query_service=ProcurementQueryService(drive_service=drive_service, json_service=drive_service.json_service),
        dual_inventory_service=dual_inventory_service,
        job_service=job_service,
        worker_service=worker_service,
        public_order_service=public_order_service,
    )

    startup_checks = config_service.validate_streamlit_secrets(security_service.load_streamlit_secrets())
    deployment_validation = config_service.validate_deployment_profile(
        system_config,
        oauth_config,
        oauth_secrets_override_active=oauth_secrets_override_active,
        oauth_config_fallback_active=oauth_config_fallback_active,
    )
    startup_blockers = list(startup_checks) + deployment_validation["blockers"]
    startup_warnings = deployment_validation["warnings"]
    runtime_environment = system_config["app"].get("runtime_environment", "local")
    if runtime_environment != "local":
        auth_service.enable_mock_auth = False
    effective_demo_mode = bool(system_config["app"].get("demo_mode")) or bool(startup_blockers)
    google_runtime_enabled = not effective_demo_mode
    long_lived_admin_runtime_enabled = security_service.admin_token_ready()
    if effective_demo_mode:
        drive_service.use_drive_api = False
        if system_config["notifications"].get("notification_mode", "mock") != "live":
            gmail_service.use_gmail_api = False
    if gmail_service.notification_mode != "live":
        gmail_service.use_gmail_api = False
    elif google_runtime_enabled:
        gmail_service.use_gmail_api = True
    google_runtime_diagnostic_service = GoogleRuntimeDiagnosticService(
        auth_service=auth_service,
        security_service=security_service,
        drive_service=drive_service,
        gmail_service=gmail_service,
        runtime_reports_root=APP_RUNTIME_DIR / "integration_reports",
        logging_service=logging_service,
    )
    latest_pilot_status = {
        "generated_at": datetime.now(UTC).isoformat(),
        "runtime_environment": system_config["app"].get("runtime_environment", "local"),
        "redirect_uri": oauth_config["google_oauth"].get("redirect_uri", ""),
        "local_runtime_status": "GO" if google_runtime_enabled and long_lived_admin_runtime_enabled else "PARTIAL",
        "deployment_runtime_status": "BLOCKED" if startup_blockers else "READY_FOR_VALIDATION",
        "notification_mode": gmail_service.describe_mode(),
        "effective_demo_mode": effective_demo_mode,
        "admin_token_ready": long_lived_admin_runtime_enabled,
        "blockers": startup_blockers,
        "warnings": startup_warnings,
        "recommendation": "NO-GO" if startup_blockers else "READY_FOR_CLOUD_VALIDATION",
    }
    config_service.write_latest_pilot_status(APP_RUNTIME_DIR / "integration_reports" / "latest_pilot_status.json", latest_pilot_status)

    session_user = auth_service.deserialize_user(st.session_state.get("user"))
    if session_user and security_service.is_admin_identity(session_user):
        requested_context = str(st.session_state.get("admin_active_context") or getattr(session_user, "active_context", None) or "platform_admin").strip().lower()
        session_user.active_context = requested_context or "platform_admin"
    effective_user = security_service.build_effective_user(session_user)

    return {
        "config_service": config_service,
        "config_issues": config_issues,
        "system_config": system_config,
        "oauth_config": oauth_config,
        "feature_flags": feature_flags,
        "subscription_plans": subscription_plans,
        "drive_service": drive_service,
        "auth_service": auth_service,
        "encryption_service": encryption_service,
        "security_service": security_service,
        "delivery_service": delivery_service,
        "gmail_service": gmail_service,
        "governance_service": governance_service,
        "audit_service": audit_service,
        "logging_service": logging_service,
        "file_lock_service": file_lock_service,
        "schema_validation_service": schema_validation_service,
        "id_allocator_service": id_allocator_service,
        "order_state_service": order_state_service,
        "token_rotation_service": token_rotation_service,
        "rollback_service": rollback_service,
        "event_dispatcher": event_dispatcher,
        "procurement_transaction_service": procurement_transaction_service,
        "order_transaction_service": order_transaction_service,
        "cache_service": cache_service,
        "dead_letter_service": dead_letter_service,
        "runtime_metrics_service": runtime_metrics_service,
        "safe_drive_write_service": safe_drive_write_service,
        "oauth_callback_service": oauth_callback_service,
        "bootstrap_service": bootstrap_service,
        "startup_recovery_service": startup_recovery_service,
        "client_service": client_service,
        "connected_accounts_service": connected_accounts_service,
        "catalog_service": catalog_service,
        "product_catalog_service": product_catalog_service,
        "manufacturer_onboarding_service": manufacturer_onboarding_service,
        "dual_inventory_service": dual_inventory_service,
        "trade_confirmation_service": trade_confirmation_service,
        "ledger_service": ledger_service,
        "ledger_reminder_service": ledger_reminder_service,
        "notification_center_service": notification_center_service,
        "job_service": job_service,
        "worker_service": worker_service,
        "public_buyer_service": public_buyer_service,
        "public_cart_service": public_cart_service,
        "public_order_service": public_order_service,
        "pricing_service": pricing_service,
        "access_portal_service": access_portal_service,
        "action_center_service": action_center_service,
        "order_query_service": OrderQueryService(drive_service=drive_service, json_service=drive_service.json_service, domain_paths_service=domain_paths_service),
        "inventory_query_service": InventoryQueryService(drive_service=drive_service, json_service=drive_service.json_service, domain_paths_service=domain_paths_service),
        "procurement_query_service": ProcurementQueryService(drive_service=drive_service, json_service=drive_service.json_service),
        "domain_paths_service": domain_paths_service,
        "startup_checks": startup_blockers,
        "startup_warnings": startup_warnings,
        "deployment_validation": deployment_validation,
        "effective_demo_mode": effective_demo_mode,
        "google_runtime_enabled": google_runtime_enabled,
        "long_lived_admin_runtime_enabled": long_lived_admin_runtime_enabled,
        "oauth_secrets_override_active": oauth_secrets_override_active,
        "oauth_config_fallback_active": oauth_config_fallback_active,
        "notification_mode": gmail_service.describe_mode(),
        "latest_pilot_status": latest_pilot_status,
        "google_runtime_diagnostic_service": google_runtime_diagnostic_service,
        "runtime_paths": {
            "base": APP_RUNTIME_DIR,
            "events": APP_RUNTIME_DIR / "events",
            "integration_reports": APP_RUNTIME_DIR / "integration_reports",
            "tokens": RUNTIME_TOKENS_DIR,
            "backups": RUNTIME_BACKUPS_DIR,
            "logs": RUNTIME_LOGS_DIR,
            "dead_letter": RUNTIME_DEAD_LETTER_DIR,
            "metrics": RUNTIME_METRICS_DIR,
            "recovery": RUNTIME_RECOVERY_DIR,
            "version_history": RUNTIME_VERSION_HISTORY_DIR,
        },
        "current_user": effective_user,
        "session_user": session_user,
        "base_role": security_service.get_base_role(session_user),
        "active_context": security_service.get_active_context(session_user),
        "is_superuser": security_service.is_admin_identity(session_user),
    }
