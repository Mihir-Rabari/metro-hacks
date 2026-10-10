# 🎫 RUNBOOK — Mihir's survival guide for tonight

*Print this in your head. Your agent (me) handles all builds — you handle
trains, pulls, and the demo.*

## Before leaving home (do ALL of these)

- [ ] `git clone https://github.com/Mihir-Rabari/metro-hacks.git` on the laptop (home WiFi)
- [ ] Laptop 100% + charger in bag (sockets on the train are limited)
- [ ] Open `dist/ops.html` and `dist/city.html` once at home so you know they work
- [ ] Phone hotspot knowledge ready (for pulling at stations)

## Timeline tonight

| Time (IST) | What | You do |
|---|---|---|
| 9:00 PM | Report at Mahatma Mandir | Forward me the problem statement the SECOND it's announced (DM the full text/links) |
| 10:00 PM | Boarding closes | I'm already building — check Discord at every station stop |
| ~10:00 PM–12:15 AM | Build window (~2 hrs) | At each station: `git pull` in the repo folder. 20 seconds on LTE. If it fails, next station — nothing is lost, work is always saved in the repo |
| ~12:15 AM | Submission prep | Form wants: **repo link** (same URL all night) + **one-line pitch** (I'll write it) + **what works** (I'll list it) |
| ~1:30 AM | Form closes (1 hr after end) | Submit — link never changed, pitch is copy-paste |

## On-train protocol (network is patchy — this is the whole trick)

1. **Problem statement arrives → paste it to me in one message.** Any format:
   photo transcription, copy-paste, voice-note-to-text. One shot is enough —
   I have full network on my box and I build end-to-end.
2. **At every station stop:** `git pull` in the repo folder. That's it.
   Optional helper: run `sync.sh` (Mac/Linux) in the repo folder — it retries
   the pull every 15 s automatically until it succeeds, then beeps.
3. **Underground / no signal:** nothing to do. I'm pushing continuously. You
   just catch up at the next stop.
4. **When you get a new build:** open `dist/app.html` (the finished app),
   click through it once. If anything looks off, tell me at the next stop.

## Demo script for the judges (~3 min, airplane-mode-proof)

1. **Open the app** from the repo folder — double-click `dist/app.html`.
   Say: "Everything you'll see runs from this one file — no internet, no server."
2. **Flip airplane mode ON with them watching.** The app detects it and shows
   the offline banner + queue badge. Nothing breaks. *(This is the resilience
   criterion, nailed visibly.)*
3. **Core flow** — whatever the problem statement was, walk the ONE flow
   end-to-end (e.g. report a fault in free text → AI triages it live as you
   type → routed to team with severity → saved locally → shows "queued · syncs
   at station").
4. **Flip airplane mode OFF.** Queue badge drains to 0, entries flip to
   "synced". *"Reports written underground sync when the train reaches a
   station — same as how we worked tonight."*
5. **Point at the data:** "All 36 stations on tonight's actual route, real
   names in Gujarati and English, real interchanges — sources and assumptions
   in `data/assumptions.md`."
6. **Feasibility:** one sentence on how GMRC could pilot it tomorrow
   (it's a static file — works on any staff PC/browser, no infra).

## Pitch skeletons (we finalize after the problem drops)

- Ops track: *"Offline-first fault-triage console for metro staff: free-text
  report → on-device AI assigns category, severity, team and SLA underground —
  syncs when the train reaches a station."*
- City track: *"Interchange companion: metro→bus→last-mile planning that works
  underground, with honest 'will I make it' math and offline maps for the
  entire corridor."*

## Fallbacks (pre-planned, not improvised)

- **No network on my pushes reach you** → everything is ALSO baked into the
  repo; you already cloned the working v1 demos at home. Worst case you demo
  `dist/ops.html` as-is — it IS a complete working prototype.
- **App crashes mid-demo** → reload the page (F5); IndexedDB keeps all data.
- **Judges ask about model details** → `scripts/train_*.py` are committed;
  show them the training script. It's reproducible and honest.
- **Asked "what's real?"** → open `data/assumptions.md`. Table. Done.

*— Hermes, your build engine for tonight. GO WIN THIS. 🚇🔥*
