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
| Auth | `PARTIAL` | Google sign-in flow exists, but deployment/runtime provisioning still needs environment-level validation. |
| RBAC | `DONE` | Active runtime roles are `platform_admin`, `manufacturer`, `mahajan`, `public_buyer`, and `worker`. |
| Admin Drive DB | `PARTIAL` | Canonical root/services exist; live cutover remains operator-controlled. |
| Sidebar | `DONE` | Readable icon + label nav restored and icon-only experiment removed. |
| Marketplace | `PARTIAL` | Public buyer browse/cart flow is stable and now acts as the reference commerce UI. |
| Products | `PARTIAL` | Catalog/product workflow exists; some seller/admin screens still carry older shell patterns. |
| Raw Materials | `PARTIAL` | Supply catalog now follows the commerce-card pattern more closely, but deeper procurement cleanup remains. |
| Suta Mandi | `PARTIAL` | Manufacturer sourcing lane now aligns better with commerce cards, but workflow polish remains. |
| MandiPlace | `PARTIAL` | Dedicated card-first cleanup is in place for requester/admin/supplier views, but some action tabs still rely on older form-first patterns. |
| Packaging | `PARTIAL` | Catalogs and order attachment flow exist; visibility is now clearer on procurement cards/details. |
| Courier | `PARTIAL` | Catalogs and logistics attachment flow exist; booking/tracking visibility is now clearer on procurement cards/details. |
| Finance | `PARTIAL` | Settlement/invoice/dispute layer exists, but it is still a JSON-first operational system. |
| Notifications | `PARTIAL` | In-app notifications and Gmail queue exist; UI/ops polish is still ongoing. |
| Jobs | `PARTIAL` | Job and worker lifecycle exists; lower-traffic screens still need cleanup. |
| Operations | `PARTIAL` | Operations/health dashboards exist; shell simplification and page consistency remain in progress. |
| Release tools | `PARTIAL` | Validation/bootstrap/migration/release scripts exist; final operator runbooks still matter. |
| Client role | `REMOVED` | Not part of live RBAC anymore. |
