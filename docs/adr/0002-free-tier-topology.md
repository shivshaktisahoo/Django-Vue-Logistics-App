# ADR 0002: Free-tier deployment topology

**Status:** accepted

## Context

This is a public portfolio demo that must stay online indefinitely at zero cost, with no trial
expiry. The target production shape is: autoscaled web pods, a separate Celery worker pool, one
beat scheduler, managed Postgres and Redis.

## Decision

| Concern | Production shape | Free-tier shape used here |
|---|---|---|
| Web | N gunicorn pods behind a load balancer | One Render free web service |
| Workers | Separate autoscaled Celery pool | Celery worker (`--pool solo`, embedded beat `-B`) as a sibling process in the web container (`bin/start-render.sh`) |
| Postgres | Managed, always-on | Neon serverless (auto-suspends); `CONN_MAX_AGE=0` |
| Redis | Managed, dedicated | Upstash serverless, with a command quota |
| Cold starts | n/a | Keep-alive ping every 10 min; the SPA pings `/health/` on load and shows an honest "waking the server" state |

Specific tunings:

- **`/api/v1/health/` never touches the database.** Keep-alive pings keep Render warm without
  keeping Neon's compute awake. `/api/v1/health/ready/` checks the DB for real.
- **The broker polls every 30 s** (`CELERY_BROKER_TRANSPORT_OPTIONS.polling_interval`, which
  kombu turns into the BRPOP timeout), and the worker runs `--without-gossip/mingle/heartbeat`.
  An idle worker then uses ~175k Redis commands a month instead of ~2.6M. Enqueued tasks still
  wake BRPOP immediately, so latency doesn't change.
- **No result backend.** Job progress (for example bulk imports) is stored on our own models, so
  the UI can show it without extra Redis traffic.
- **Live vehicle positions are computed, not stored.** A position is interpolated along the
  route from departure time and ETA when it's read, instead of a beat task writing a GPS ping
  every minute. That writing would keep the database awake around the clock.

## Consequences

- A beat task can be missed while the dyno sleeps. The keep-alive mitigates this, and every
  scheduled job is idempotent and catch-up safe (for example the nightly demo reset).
- One process restart takes the worker down with the web. That's acceptable for a demo; the
  production shape above removes it.
