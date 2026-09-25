# ADR 0001: Shared-schema multi-tenancy with code-defined RBAC

**Status:** accepted

## Context

A freight forwarder's data (shipments, customers, carrier rates) is commercially sensitive, and
one platform hosts many forwarders. Inside a forwarder, four very different audiences use the
same API: internal admins, ops coordinators, their customers (shippers) and their subcontracted
carriers.

## Decision

- **Shared schema, tenant column.** Every tenant-owned table inherits `core.models.TenantModel`
  (`org` FK, UUID primary key). Querysets start from `.for_org(request.org)`.
- **Tenant from a header, checked against membership.** `X-Org-Id` is resolved in
  `core.tenancy.TenantScopedMixin.initial()` *after* JWT auth. A non-member gets **404**, not
  403, so org IDs can't be probed.
- **Roles in code, not rows.** `organizations/permissions.py` maps each role to permission codes.
  Every tenant view declares `required_permissions` per action; an action without an entry is
  denied (closed by default).
- **Row-level scoping on top of RBAC.** Customers see only shipments booked for their own
  account, and carriers only their own bids and trips. That filter lives in each module's
  `selectors.py`, so views can't forget it.

## Consequences

- Cheap to run (one database, one schema) and simple to back up.
- Isolation relies on discipline in selectors. It's enforced by tests that call every endpoint as
  a member of another org, and as each role.
- Postgres row-level security would be defence in depth later; it isn't needed to be correct.
