# Data & Assumptions — read before you judge 🙂 (and judges, before you ask)

Built for **Metro Hacks — Road to DevFest Gandhinagar 2026** (onboard the Gujarat Metro,
Mahatma Mandir ⇄ APMC, 10 Oct 2026). No dataset was provided by the organizers —
per the brief, we brought our own. Here is exactly what is real, what is modeled,
and how we made that choice. Every file in `data/` carries a `meta.note` saying the same.

## ✅ Verified real (public sources, fetched 10 Oct 2026)

| What | Source | Where used |
|---|---|---|
| Complete station list of the Yellow Line (Mahatma Mandir → Motera Stadium, 21 stations) **in order**, with Gujarati names, opening dates, layout, and interchange facts | Wikipedia — "Yellow Line (Ahmedabad Metro)" station table (en) | `data/stations.json` |
| Complete station list of the Red Line (Motera Stadium → APMC, 15 incl. 1 under construction) **in order**, same fields | Wikipedia — "Red Line (Ahmedabad Metro)" station table (en) | `data/stations.json` |
| Network facts: 4 lines, 56 stations, 65.32 km, Yellow = 23.84 km / Red = 16.64 km, 3-coach trains, 750V DC third rail, GMRC operator, line opening dates incl. the 11 Jan 2026 Mahatma Mandir extension | Wikipedia — "Ahmedabad Metro" | `data/stations.json`, pitch |
| Interchange facts: Motera (Yellow↔Red), Old High Court (↔Blue), Gandhigram (Indian Railways), APMC (GSRTC bus stand), Ranip (BRTS+GSRTC), Mahatma Mandir (Gandhinagar Capital railway), GNLU (↔Violet/GIFT City), Sabarmati (HSR under construction) | Wikipedia line tables | `data/lastmile.json` `facts` |
| Station coordinates — 24 of 36 are exact OSM station/stop nodes (`coordSource: osm-station`) | OpenStreetMap via Photon geocoder | `data/stations.json` |
| Offline map tiles | OpenStreetMap / CARTO dark basemap, bulk-vendored into the repo | `kit/vendor/leaflet/tiles/` |

## 🟡 Approximated (flagged per-station in `coordSource`)

- `osm-area` (Sector-1, Sector-16, Sector-24): sector/neighbourhood centroid from OSM — the
  stations are new (opened 2024–2026) and not all have exact station nodes mapped yet.
- `osm-poi` (Vishwakarma College, Akshardham, Sabarmati Railway Stn): station is named after a
  landmark; we use the landmark's OSM node.
- `interp` (Sector-24, Koteshwar Road, Narmada Canal, Infocity, Sector-10A, Paldi):
  straight-line interpolation between verified neighbouring stations on the alignment.
  Error bound ≈ one inter-station gap (~1.2 km).
- Distances are haversine between coordinates; chain totals come to 22.8 km (Yellow) and
  15.7 km (Red) vs. official 23.84 / 16.64 — the gap is track curvature vs. straight line,
  which the app states where km are shown.

## 🟠 Modeled on public patterns (synthetic but defensible)

| Dataset | Model | Why it's defensible |
|---|---|---|
| `timetable.json` headways (10/15/20 min by hour), 06:20–22:00 window | Typical GMRC reported service pattern | Publicly reported in press; app shows "modeled" note |
| `fares.json` ₹5/10/15/20/25 slabs (2/4/8/14 km) | GMRC's published slab structure | Slab shape from GMRC fare charts in press coverage; exact slab distances may differ |
| `assets.json` per-station lift/escalator/gate/CCTV counts | Typical elevated 2-platform station | Real per-station inventory isn't public; counts are realistic ranges |
| `faults-seed.json` 120-entry 30-day history | Written in GMRC staff-report voice | The judges asked for realistic sample data — this is training/demo history |
| `lastmile.json` feeder routes (F-series) + auto fares | Interchange facts are real (above); feeder IDs/fares are indicative | A pilot would plug in AMTS/BRTS/GSRTC GTFS |
| `crowding.json` + `models/crowding.json` | Trained on synthetic data with documented commute patterns (Gandhinagar→Ahmedabad morning peak etc.) | Model is honest about being an expectation engine, MAE 7.2 pts on holdout |
| `models/triage.json` | Trained on 660 synthetic staff-style fault reports | Training script committed (`scripts/train_triage.py`) — fully reproducible |

## The point

The **transit facts (stations, order, names, connections, openings, geography) are real and
cited**; the **operational layers (timings, fares, crowding, history) are honestly modeled**
and every screen that shows modeled data says so. That's the "be ready to explain your
assumptions" criterion, answered up front.

## Offline-ness

Everything runs from a single baked file (`dist/ops.html` / `dist/city.html`): no CDN, no
fetch(), no fonts, tiles inlined. Verified by `scripts/bake.py` asserting zero external refs.
Judges can flip airplane mode — the app *notices* (online/offline events) and shows the
queue draining when connectivity returns.
