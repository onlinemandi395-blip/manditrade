# MandiTrade Phase Tracker

Current focus: feature-first recovery and UI stabilization.

Status meanings:
- `DONE`
- `PARTIAL`
- `BROKEN`
- `NOT_STARTED`
- `REMOVED`

| Area | Status | Notes |
| --- | --- | --- |
| Auth | `PARTIAL` | Google sign-in flow exists, and invited identities now stay approval-gated until ACTIVE, but deployment/runtime provisioning still needs environment-level validation. |
| RBAC | `DONE` | Active runtime roles are `platform_admin`, `manufacturer`, `mahajan`, `public_buyer`, and `worker`. |
| Identity Governance | `PARTIAL` | Admin manufacturer, mahajan, and worker governance screens now exist with completeness/trust summaries, but invitation analytics and deeper self-service completion are still maturing. |
| Admin Drive DB | `PARTIAL` | Canonical root/services exist; live cutover remains operator-controlled. |
| Inventory Engine | `PARTIAL` | Unified inventory records, reservations, and movement ledger now exist across marketplace, MandiPlace, raw materials, and suta, but some lower-traffic screens still use older quantity summaries. |
| Sidebar | `DONE` | Readable icon + label nav restored and icon-only experiment removed. |
| Marketplace | `PARTIAL` | Public buyer browse/cart flow is stable, and product cards now show live stock state with reservation on order creation. |
| Products | `PARTIAL` | Catalog/product workflow exists; some seller/admin screens still carry older shell patterns. |
| Raw Materials | `PARTIAL` | Supply catalog now follows the commerce-card pattern more closely and shows unified inventory stock states, but deeper procurement cleanup remains. |
| Suta Mandi | `PARTIAL` | Manufacturer sourcing lane now aligns better with commerce cards and stock-state visibility, but workflow polish remains. |
| MandiPlace | `PARTIAL` | Dedicated card-first cleanup is in place for requester/admin/supplier views, and supplier stock is now reservation-driven, but some action tabs still rely on older form-first patterns. |
| Packaging | `PARTIAL` | Catalogs and order attachment flow exist; visibility is now clearer on procurement cards/details. |
| Courier | `PARTIAL` | Catalogs and logistics attachment flow exist; booking/tracking visibility is now clearer on procurement cards/details. |
| Finance | `PARTIAL` | Settlement/invoice/dispute layer exists, but it is still a JSON-first operational system. |
| Notifications | `PARTIAL` | In-app notifications and Gmail queue exist; UI/ops polish is still ongoing. |
| Jobs | `PARTIAL` | Job and worker lifecycle exists; worker identity governance is stronger now, but lower-traffic job screens still need cleanup. |
| Operations | `PARTIAL` | Operations/health dashboards exist; shell simplification and page consistency remain in progress. |
| Release tools | `PARTIAL` | Validation/bootstrap/migration/release scripts exist; final operator runbooks still matter. |
| Client role | `REMOVED` | Not part of live RBAC anymore. |
