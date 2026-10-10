# Fariyad — sync backend (Node.js + MongoDB via Docker)

The "station-side" server of the offline-first architecture. The app files,
triages and queues complaints **fully on-device**; when connectivity returns
(train at a station), the outbox drains to this backend. If the backend is
unreachable, tickets **stay queued** — that is the design, not a failure mode.

## Run the frozen stack (one command)

```bash
cd backend
docker compose up -d --build
# dashboard: http://localhost:3020   ·   API: POST /api/sync, GET /api/tickets, GET /api/stats, GET /health
```

- **mongo** — MongoDB 7, data in a named volume
- **backend** — Node 22 + Express + the official MongoDB driver, listening on `:3020`

## API contract (what the Android app's outbox drains into)

```
POST /api/sync
{ "deviceId": "mihir-pixel", "tickets": [ { id, text, lang, category, engine,
    severity, urg, team, sla, channel, station, reply, created } ] }
→ { "ok": true, "acked": ["r-…-…"], "failed": [], "serverTime": 1760430000000 }
```

Upsert keyed on the ticket `id` — drains are idempotent, so retries after a
dropped connection never duplicate tickets.

```
GET /api/tickets?limit=50   newest tickets first
GET /api/stats              { total, s1, avgUrg, byDept: [{ dept, n, maxUrg }] }
GET /health                 liveness + mongo status
```

`/` serves the live control-room dashboard (auto-refreshing every 4 s).

## Why this is the pilot story

GMRC already runs complaint channels (app, helpline, social desk). This backend
shows the exact shape of the receiving side: department-aware storage, urgency
aggregation, per-device dedupe. The sync contract is ~20 lines of HTTP — the
same envelope a GMRC backend would consume.
