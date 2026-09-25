#!/usr/bin/env bash
# Free-tier topology: one Render web service runs the API *and* Celery.
#
# Render's free plan has no background-worker service, so the Celery worker (with
# an embedded beat scheduler, -B) runs as a sibling process in the same container.
# In production this would be a separate autoscaled worker pool plus one beat; the
# tradeoff is documented in docs/adr/0002-free-tier-topology.md.
set -euo pipefail

python manage.py migrate --noinput
python manage.py seed_demo

if [[ -n "${REDIS_URL:-}" ]]; then
  # --without-gossip/mingle/heartbeat: no chatter between workers (there is only one),
  # which keeps idle Redis traffic inside the free plan's command quota.
  celery -A config worker -B --pool solo --concurrency 1 --loglevel INFO \
    --without-gossip --without-mingle --without-heartbeat \
    --schedule /tmp/celerybeat-schedule &
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 60 \
  --access-logfile - --forwarded-allow-ips "*"
