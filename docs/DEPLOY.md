# Deploying CargoPulse (free tier, no credit card)

| Piece | Service | Free-plan notes |
|---|---|---|
| API + Celery worker/beat | **Render** web service | Sleeps after ~15 min idle; the keep-alive workflow prevents that |
| PostgreSQL | **Neon** | Compute auto-suspends when idle; the liveness ping deliberately skips the DB |
| Redis (Celery broker, cache) | **Upstash** | Monthly command quota; the worker polls every 30 s to stay under it |
| Frontend (Vue SPA) | **Vercel** | Proxies `/api/*` to Render, so the auth cookie is first-party |

Total time: about 20 minutes.

## 1. Push the repo to GitHub

```bash
git push -u origin main
```

## 2. Postgres on Neon

1. Sign up at <https://neon.tech> → **New project** (region: Frankfurt / `eu-central-1`, close to Render Frankfurt).
2. Copy the **pooled** connection string. It looks like
   `postgresql://user:pass@ep-xxx-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require`.

## 3. Redis on Upstash

1. Sign up at <https://upstash.com> → **Create database** → Redis, region `eu-central-1`, TLS on.
2. Copy the `rediss://default:…@….upstash.io:6379` URL.

## 4. API on Render

1. Sign up at <https://render.com> with GitHub → **New → Blueprint** → pick this repo.
   Render reads `render.yaml` and creates `cargopulse-api`.
2. When prompted, paste `DATABASE_URL` (Neon) and `REDIS_URL` (Upstash).
3. The first deploy runs migrations and `seed_demo` automatically (see `backend/bin/start-render.sh`).
4. Check it: `https://cargopulse-api.onrender.com/api/v1/health/` → `{"status": "ok"}`.

> If Render gives the service a different URL (the name was taken), update the
> `/api` rewrite in `frontend/vercel.json` to match.

Optional: create an admin for `/admin/` from the Render **Shell** tab:
`python manage.py createsuperuser`.

## 5. Frontend on Vercel

1. Sign up at <https://vercel.com> with GitHub → **Add New → Project** → pick this repo.
2. **Root directory:** `frontend`. Vercel detects Vite; `vercel.json` sets the rest.
3. Deploy, open the URL, click a demo persona.

## 6. Keep the demo warm

In GitHub → **Settings → Secrets and variables → Actions → Variables**, add
`API_HEALTH_URL = https://cargopulse-api.onrender.com/api/v1/health/`.
The `Keep demo warm` workflow pings it every 10 minutes.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Login page says "Waking the demo server" for >60 s | Render build or boot failed. Check its **Logs** tab. |
| Demo buttons say "workspace is being prepared" | `seed_demo` hasn't run. Run it from the Render Shell. |
| Signed out on every reload | The `/api` rewrite points at the wrong host, so the refresh cookie isn't first-party. |
| `DisallowedHost` | Render sets `RENDER_EXTERNAL_HOSTNAME` itself; for a custom domain add it to `DJANGO_ALLOWED_HOSTS`. |
