# CargoPulse

A multi-tenant freight forwarding and shipment visibility platform: bookings, milestone tracking,
carrier tendering, trip execution and a customer portal across air, ocean and road.

**Stack:** Django 5 · Django REST Framework · PostgreSQL · Celery + Redis · Vue 3 · TypeScript ·
Vuetify 3 · TanStack Query

> Portfolio project by Shiv Shakti Sahoo. It models the kind of platform I build professionally
> for freight forwarders and 3PLs.

## Try it

Open the live demo and pick a persona. There's no signup; each persona sees a different product:

| Persona | What they can do |
|---|---|
| **Admin** | Everything, including team and organization settings |
| **Ops Coordinator** | Book shipments, run tenders, manage exceptions and trips |
| **Customer** | Shipper portal: only their own shipments and documents |
| **Carrier** | Bid on open tenders, run assigned trips, upload proof of delivery |

Visitors can create and edit freely. The demo workspace is rebuilt every night.

## Status

| Phase | Scope | State |
|---|---|---|
| 1. Foundation | Multi-tenant orgs, 4-role RBAC, JWT with an httpOnly refresh cookie, one-click demo personas, CI, free-tier deploy pipeline | ✅ |
| 2. Shipments core | Master data (UN/LOCODE locations, carriers, fleet, customer address books), booking form with live chargeable weight, ISO 6346 container validation, status state machine, milestones, audit trail | ✅ |
| 3. Tracking & exceptions | Live map with positions computed along real sea lanes (Malacca, Suez, Hormuz) and great-circle air routes; public no-login tracking page; rule engine that raises, escalates and auto-clears exceptions (past ETA, ETA at risk, stale tracking, customs dwell, long holds) with an acknowledge/assign/resolve workflow | ✅ |
| 4. Carrier bidding & trips | Tenders, sealed bids, auto-close, award → trip, POD | ⏳ |
| 5. Bulk ops & integration | CargoWise-style XML/CSV import with async progress, bulk updates, signed webhooks | ⏳ |
| 6. Notifications | Email/WhatsApp adapters, rules, outbox | ⏳ |
| 7. Control tower & reports | KPIs, carrier scorecards, query-optimization lab | ⏳ |
| 8. Polish | Landing page, screenshots, end-to-end tests | ⏳ |

## Architecture

```
Vue 3 SPA (Vuetify, Pinia, TanStack Query) ──/api──► Django 5 + DRF (gunicorn)
                                                         │
                                  ┌──────────────────────┼──────────────────────┐
                              PostgreSQL              Redis               Celery worker + beat
                          (system of record)     (broker, cache)     (imports, notifications,
                                                                         SLA checks, resets)
```

- **Modular monolith.** Each bounded context is a Django app. Apps talk through `services.py`
  (writes, transactions, business rules) and `selectors.py` (reads, tenant and row scoping), never
  through each other's views.
- **Tenancy.** Every tenant row carries `org`. The active org comes from `X-Org-Id` and is checked
  against membership; non-members get 404. See [ADR 0001](docs/adr/0001-multi-tenancy-and-rbac.md).
- **RBAC is closed by default.** Each endpoint declares a permission per action, and roles map to
  permission codes in code.
- **Auth.** A short-lived access JWT is held in memory. The refresh JWT is rotated, blacklisted
  after use, and kept in an httpOnly cookie scoped to `/api/v1/auth/`. The SPA does a
  single-flight refresh on 401.
- **Reference numbers** (`SHP-2026-000123`) come from a row-locked counter, so they're gap-free
  and safe under concurrent bookings.
- **Maps.** Leaflet with keyless Esri Gray Canvas basemaps (swap via `VITE_MAP_TILES_LIGHT` / `VITE_MAP_TILES_DARK`).
  Vehicle positions are interpolated along the route from departure time and ETA, not stored as pings.
- **Free-tier engineering.** See [ADR 0002](docs/adr/0002-free-tier-topology.md): the in-process
  worker, a health check that skips the DB, and Redis command budgeting.

## Run locally

```bash
cp .env.example .env
docker compose up --build        # web on :5173, API on :8000, Swagger at /api/schema/swagger/
```

Without Docker, the backend falls back to SQLite and runs Celery tasks eagerly:

```bash
cd backend && python -m venv .venv && .venv/Scripts/activate   # or: source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate && python manage.py seed_demo && python manage.py runserver

cd frontend && npm install && npm run dev                      # proxies /api to :8000
```

## Tests

```bash
cd backend && pytest && ruff check . && ruff format --check .
cd frontend && npm run typecheck && npm test && npm run build
```

## Deploy

See [docs/DEPLOY.md](docs/DEPLOY.md): Render + Neon + Upstash + Vercel, all on free plans.
