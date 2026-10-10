# 🚇 Metro Hacks — Road to DevFest Gandhinagar 2026

Built **on board the Gujarat Metro** (Mahatma Mandir ⇄ APMC, 10 Oct 2026) for the
first-ever hackathon on a running metro train in Gujarat. Solo build.

**This repo is an offline-first transit toolkit**: every asset needed to demo with
airplane mode ON is vendored into the repository itself — real station data for the
actual ride, trained AI models that run in-browser, offline map tiles, and two
working prototype flows (one per track) that can be morphed into the final
problem solution the moment the problem statement drops.

## 🎯 Why this shape

The brief scores: relevance, working prototype, **resilience (airplane-mode demo)**,
technical depth (AI doing meaningful work), feasibility. Every choice below maps
to a scoring line:

| Choice | Scores |
|---|---|
| Single-file baked demo (`dist/*.html`) — double-click, zero network | Resilience |
| Naive Bayes fault triage trained offline, inference in JS | Technical depth |
| IndexedDB + outbox: reports queue offline, drain when signal returns ("sync at station") | Resilience + relevance |
| Real 36-station dataset for tonight's actual route, Gujarati names included | Relevance |
| `data/assumptions.md` — what's real vs. modeled, per field | Feasibility + the brief's own "explain your assumptions" |

## 🚀 Run it (offline, no server, no internet)

1. Clone the repo **before boarding** (network needed once).
2. Open **`dist/ops.html`** (Metro Operations demo) or **`dist/city.html`**
   (City Transport demo) — double-click, any modern browser.
3. Flip airplane mode. Everything keeps working — the app shows it noticed.

Rebuild the single-file demo after editing:

```bash
python3 scripts/bake.py ops    # -> dist/ops.html
python3 scripts/bake.py city   # -> dist/city.html
```

Dev mode (served): `python3 -m http.server` then open
`templates/ops/index.html` or `templates/city/index.html`.

## 📦 What's inside

```
dist/            baked single-file demos (DEMO THESE — zero network refs)
templates/       ops/ (fault log · live board · delay simulator)
                 city/ (offline map · will-I-make-my-bus · fare calc)
kit/             dash.css design system · store.js (IndexedDB+outbox)
                 ai.js (in-browser inference) · util.js · map.js
                 vendor/ (Chart.js, Leaflet, 250 offline dark tiles)
models/          triage.json (naive Bayes, 660 examples, 10 categories)
                 crowding.json (CART tree, holdout MAE 7.2)
data/            stations.json (36 real stations, tonight's route, en+gu)
                 timetable/fares/assets/faults-seed/lastmile/busroutes/crowding
                 assumptions.md  ← real vs modeled, judged-friendly honesty
scripts/         train_triage.py · train_crowding.py · gen_data.py
                 fetch_tiles.py · bake.py (single-file baker)
```

## 🤖 The AI (no cloud, no API keys, airplane-mode safe)

- **Fault triage** — trained in Python (committed, reproducible), runs in ~40 lines
  of JS: free-text staff report → category (10 classes) + severity (S1/S2/S3) +
  owning team + SLA, with confidence. Try: *"lift stuck between ground and
  concourse, passengers inside"* → `S1 → Lifts & Escalators (Mechanical) → IMMEDIATE`.
- **Crowding predictor** — CART regression tree walked in JS: station class ×
  hour-bucket × direction → expected occupancy per coach.

## 🗺 Data honesty

See [`data/assumptions.md`](data/assumptions.md). Short version: stations, order,
names, interchanges and openings are real (Wikipedia/OSM, fetched 10 Oct 2026);
timings, fares and histories are honestly modeled with sources and error bounds,
and every UI surface labels modeled numbers.

## Route facts for the ride

Mahatma Mandir → Motera Stadium (Yellow, 21 stn, ~24 km) → APMC (Red, 14 stn,
~17 km) and back. The repo contains every station on tonight's actual route.

---
*Data: Wikipedia (CC BY-SA) + OpenStreetMap (ODbL) via Photon geocoder; tiles © OpenStreetMap contributors, dark basemap by CARTO.*
