# 📦 Fariyad — Dataset Inventory

No dataset was provided by the organizers — the brief said *bring your own*.
So every dataset here carries its provenance on its sleeve. Full methodology:
**[data/assumptions.md](../data/assumptions.md)** (the "read before you judge"
doc). This page is the quick index.

## Status legend

- 🟢 **Real** — fetched from a public source, verifiable
- 🟡 **Approximated** — real data, derived with a flagged method (per-record `coordSource`)
- 🟠 **Modeled** — synthetic, built on publicly reported patterns; every file says so in `meta.note`

## The datasets

| File | What | Rows | Status | Used by |
|---|---|---|---|---|
| `stations.json` | Complete Yellow (21) + Red (15) Line station lists **in order**, English + Gujarati names, layouts, interchanges, coordinates | 36 | 🟢 list & facts 🟡 coords (24/36 exact OSM nodes; rest flagged `osm-area`/`osm-poi`/`interp`) | app, ops, city |
| `timetable.json` | Service pattern 06:20–22:00, headways 10/15/20 min by hour | per-station | 🟠 (press-reported pattern) | ops, city |
| `fares.json` | ₹5/10/15/20/25 slabs at 2/4/8/14 km | 5 slabs | 🟠 (GMRC's published slab *shape*) | city |
| `busroutes.json` | Feeder bus legs at interchanges | 20+ | 🟠 (IDs indicative; interchanges real) | city |
| `lastmile.json` | Station-exit → sector walk/auto/BRTS/GSRTC connections + verified interchange facts | 36×N | 🟢 facts 🟠 feeds | city (PS-05 demo) |
| `assets.json` | Per-station lift/escalator/gate/CCTV inventory | 36 | 🟠 realistic ranges (real inventory not public) | ops (PS-03 demo) |
| `faults-seed.json` | 30-day maintenance history in GMRC staff-report voice | 120 | 🟠 training/demo history | ops |
| `complaints-seed.json` | Demo complaint history across 4 languages/scripts | 150 | 🟠 (39 Gujarati-script, 12 Devanagari, rest Latin) | app (Fariyad) |
| `replies.json` | Draft-reply composition blocks (openers / actions / closers / SLA lines) per detected language, filled with `{station}` `{id}` `{sla}` at generation time | 5 block sets | authored | app |
| `crowding.json` | Trained crowding regression tree | 2,200 train | 🟠 | ops |
| `models/triage.json` | Trained Naive Bayes (11 categories) | 1,248 train | 🟠 | app |
| `android/…/assets/www/models/centroids.json` | 11×384 category centroids computed from the public multilingual encoder (fastembed, offline) | 11 | derived from public model | app (APK) |

## Model & code assets (vendored, offline)

| Asset | What | Size |
|---|---|---|
| `kit/vendor/` | Leaflet + Chart.js UMD builds + 250 dark CARTO basemap tiles (z13, corridor-fitting) | ~1.5 MB |
| `android/…/assets/www/transformers.min.js` | transformers.js UMD (ONNX Runtime Web bundled) for the APK | 898 KB |
| `android/…/assets/www/models/multilingual-minilm/` | Tokenizer + config for the HF model (committed); **ONNX q8 weights fetched by CI at build time** — 118 MB never enters git | 17 MB in git |
| `dist/app.html` | Fariyad console, fully inlined | 688 KB |

## The honesty rule

Every JSON file in `data/` embeds a `meta.note` stating its provenance in the
same words as [assumptions.md](../data/assumptions.md). If a judge opens any
single file cold, the file itself declares what is real. That's not modesty —
it's the brief's own judging criterion (*"be ready to explain your
assumptions"*), met at the file level.
