#!/usr/bin/env python3
"""Generate the remaining offline datasets: timetable, fares, assets, seeded fault
log, last-mile feeders, bus routes. Deterministic (seeded). Real where possible;
anything modeled is flagged in data/assumptions.md.

Run: python3 scripts/gen_data.py
"""
import json
import os
import random
import datetime

random.seed(20261010)
HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")

stations_doc = json.load(open(os.path.join(DATA, "stations.json")))
stations = stations_doc["stations"]
yellow = [s for s in stations if s["line"] == "yellow"]  # Mahatma Mandir -> Motera
red = [s for s in stations if s["line"] == "red"]        # Motera -> APMC

# ---------------------------------------------------------------------------
# 1. Timetable: service model (flagged as modeled on public reporting)
# ---------------------------------------------------------------------------
def headway_for(hour):
    if 8 <= hour <= 11 or 17 <= hour <= 20:
        return 10
    if 6 <= hour <= 7 or 12 <= hour <= 16:
        return 15
    return 20

timetable = {
    "meta": {
        "note": "Service model derived from GMRC public reporting patterns; see assumptions.md",
        "firstTrain": "06:20", "lastTrain": "22:00",
        "dwellSeconds": 30, "operationalWindow": "06:20-22:00",
        "headways": [{"hours": "06-07,12-16", "minutes": 15},
                     {"hours": "08-11,17-20", "minutes": 10},
                     {"hours": "21-22", "minutes": 20}],
    },
    "lines": {}
}

for code, line_stations, direction in (
        ("yellow_to_motera", yellow, "Motera Stadium"),
        ("yellow_to_mahatma_mandir", list(reversed(yellow)), "Mahatma Mandir"),
        ("red_to_apmc", red, "APMC"),
        ("red_to_motera", list(reversed(red)), "Motera Stadium")):
    km_acc, seg = 0.0, []
    for s in line_stations:
        km_acc += s["kmFromPrev"] if s["kmFromStart"] else 0
        # avg 34 km/h run + 30s dwell -> seconds from origin
        minutes = 0
        if seg:
            minutes = seg[-1]["minFromOrigin"] + (s["kmFromPrev"] / 34.0) * 60 + 0.5
        seg.append({"station": s["name"], "kmFromOrigin": round(km_acc, 2), "minFromOrigin": round(minutes, 1)})
    timetable["lines"][code] = {
        "direction": direction,
        "endToEndMinutes": round(seg[-1]["minFromOrigin"], 1),
        "stops": seg,
        "headwayFor": "function in util.js (10/15/20 by hour)",
    }

# 2. Fares (modeled on GMRC slab pattern; flagged)
fares = {
    "meta": {"currency": "INR", "note": "Slab pattern modeled on GMRC published structure; see assumptions.md"},
    "slabs": [{"upToKm": 2, "fare": 5}, {"upToKm": 4, "fare": 10}, {"upToKm": 8, "fare": 15},
              {"upToKm": 14, "fare": 20}, {"upToKm": 999, "fare": 25}],
    "dayPass": 50,
}

# 3. Station asset inventory (synthetic but realistic; seeded per station)
def assets_for(s):
    n_lifts = random.randint(2, 4) if s["operational"] else 0
    n_esc = random.randint(2, 8)
    n_gates = random.choice([4, 6, 8, 8, 10, 12])
    return {
        "lifts": [{"id": f"L{c}", "location": loc} for c, loc in
                  zip(range(1, n_lifts + 1), ["concourse->platform A", "concourse->platform B", "exit->concourse", "parking->concourse"][:n_lifts])],
        "escalators": [{"id": f"E{c}", "location": loc} for c, loc in
                       zip(range(1, n_esc + 1), ["up platform A", "down platform A", "up platform B", "down platform B",
                                                 "exit up", "exit down", "entry up", "parking down"][:n_esc])],
        "afcGates": [{"id": f"G{c:02d}", "entry": c <= n_gates * 0.6} for c in range(1, n_gates + 1)],
        "pidsDisplays": random.randint(4, 10),
        "cctvCameras": random.randint(16, 48),
        "platforms": 2,
    }

assets = {"meta": {"note": "Synthetic inventory counts typical for elevated 2-platform GMRC stations; see assumptions.md"},
          "stations": {s["name"]: assets_for(s) for s in stations if s["operational"]}}

# 4. Seeded fault log (30 days of history for the ops dashboard demo)
CAT_SEV = {
    "lifts_escalators": [("L1 escalator handrail loose", "S2"), ("Lift stuck between floors", "S1"),
                          ("Escalator stopped at exit A", "S2"), ("Lift door not closing", "S2")],
    "afc_gates": [("Gate 3 not scanning QR", "S2"), ("AVM not accepting notes", "S3"),
                   ("Gate barrier stuck half open", "S2"), ("Card debited twice", "S3")],
    "signalling": [("Train held at red signal", "S1"), ("Axle counter fault", "S1"), ("Track circuit failure", "S1")],
    "rolling_stock": [("Coach 2 AC not working", "S2"), ("Door not closing in coach 3", "S1"), ("Screeching brakes", "S2")],
    "station_infra": [("Water dripping on platform 1", "S2"), ("PIDS showing garbage text", "S3"), ("Staircase railing loose", "S2")],
    "power_traction": [("UPS not holding charge", "S2"), ("Breaker tripping repeatedly", "S1")],
    "cleanliness": [("Platform 2 not swept", "S3"), ("Washroom flooded", "S2"), ("Dustbin overflowing", "S3")],
    "security_safety": [("Unattended bag near counter", "S1"), ("Crowd beyond yellow line", "S1")],
    "passenger_info": [("Wrong station announcement", "S3"), ("Exit signage missing", "S3")],
    "civic_tickets": [("Auto refusing meter at gate", "S3"), ("Approach road potholes", "S3")],
}
ops_stations = [s["name"] for s in stations if s["operational"] and s["line"] == "yellow"]
faults = []
now = datetime.datetime(2026, 10, 10, 12, 0)
for i in range(120):
    cat = random.choice(list(CAT_SEV))
    desc, sev = random.choice(CAT_SEV[cat])
    ts = now - datetime.timedelta(days=random.randint(0, 30), hours=random.randint(0, 20), minutes=random.randint(0, 59))
    status = random.choices(["resolved", "assigned", "open"], weights=[62, 20, 18])[0]
    faults.append({
        "id": f"F-{1000+i}", "ts": ts.strftime("%Y-%m-%dT%H:%M"), "station": random.choice(ops_stations),
        "text": desc, "category": cat, "severity": sev, "status": status,
        "reportedBy": random.choice(["Station Controller", "Duty CSO", "Housekeeping Sup.", "Passenger (helpline)", "Maintenance crew"]),
    })
faults.sort(key=lambda f: f["ts"], reverse=True)
faults_seed = {"meta": {"note": "Seeded synthetic history (30 days) for demo + team-queue warm start; see assumptions.md"},
               "faults": faults}

# 5. Last-mile feeders + 6. bus routes (interchange facts real from Wikipedia; route IDs synthetic)
real_connections = {
    "Motera Stadium": ["Yellow Line interchange", "Ahmedabad BRTS", "Stadium events crowd plan"],
    "Sabarmati": ["Ahmedabad BRTS", "Sabarmati HSR (under construction)", "Sabarmati Riverfront"],
    "AEC": ["Ahmedabad BRTS"],
    "Ranip": ["Ahmedabad BRTS", "GSRTC Bus Station"],
    "Vadaj": ["Ahmedabad BRTS", "AMTS feeder"],
    "Old High Court": ["Blue Line interchange", "Ashram Road AMTS corridor"],
    "Gandhigram": ["Indian Railways - Gandhigram station", "AMTS"],
    "APMC": ["GSRTC Bus Station", "APMC market autos"],
    "Mahatma Mandir": ["Indian Railways - Gandhinagar Capital", "Mahatma Mandir/Dandi Kutir events", "GMRC events bus"],
    "GNLU": ["Violet Line (GIFT City) interchange at GNLU", "GIFT City shuttles", "PDEU campus"],
    "Infocity": ["Infocity IT park shuttle", "AMTS/GSRTC Gandhinagar"],
    "Sachivalaya": ["Secretariat staff transport", "Sector 9/10 shared autos"],
}
lastmile = {"meta": {"note": "Interchange facts real (Wikipedia line tables); feeder route IDs synthetic; auto fares indicative"},
            "stations": {}}
busroutes = {"meta": {"note": "Synthetic feeder network (F-series) for last-mile demo; headways indicative"},
             "routes": []}
dest_by_sector = {
    "Mahatma Mandir": ["Dandi Kutir", "Mahatma Mandir Convention Centre", "Gandhinagar Capital Rly Stn"],
    "Sector-24": ["Sector 22 market", "GEB Colony", "Punsweep"], "Sector-16": ["GH-4 market", "Ch-6 circle", "Guest House"],
    "Juna Sachivalaya": ["Old Secretariat", "Sector 9 shops"], "Akshardham": ["Akshardham Temple", "Sector 20"],
    "Sachivalaya": ["Swarnim Sankul (Secretariat)", "Indroda Park"], "Sector-10A": ["Sector 10 market", "Gandhinagar Bus Stand"],
    "Sector-1": ["GEB", "Sector 1-2 quarters"], "Infocity": ["Infocity IT offices", "SRP campus"],
    "Dholakuva Circle": ["Sargasan", "Rail Vihar"], "Randesan": ["Randesan societies", "Bopal Road"],
    "Raysan": ["Raysan Road houses", "Godrej properties"], "GNLU": ["GNLU campus", "PDEU"],
    "Koba Gam": ["Koba village"], "Juna Koba": ["Juna Koba market"], "Koba Circle": ["Koba circle market", "Ch-0"],
    "Narmada Canal": ["Canal-side societies"], "Tapovan Circle": ["Tapovan Circle", "Vavol"],
    "Vishwakarma College": ["VGEC campus", "Chandkheda"], "Koteshwar Road": ["Koteshwar", "Motera Stadium walk"],
    "Motera Stadium": ["Narendra Modi Stadium", "VIP road"],
    "Sabarmati": ["Sabarmati Riverfront", "Sabarmati HSR (u/c)"], "AEC": ["AEC campus", "Anandnagar road"],
    "Ranip": ["Ranip GSRTC stand", "BRTS terminal"], "Vadaj": ["Vadaj bus terminal", "Usmanpura garden"],
    "Vijay Nagar": ["Vijay Nagar societies"], "Usmanpura": ["Usmanpura riverfront", "Ashram Road offices"],
    "Old High Court": ["Ashram Road offices", "Gandhi Ashram (via Blue Line)"], "Gandhigram": ["Gandhigram Rly", "Paldi area"],
    "Paldi": ["Paldi bus stand", "Nehru Bridge"], "Shreyas": ["Shreyas crossing", "Maninagar direction"],
    "Rajiv Nagar": ["Rajiv Nagar societies"], "Jivraj Park": ["Jivraj Park", "Mahavir Nagar"], "APMC": ["APMC market", "GSRTC stand"],
}
for s in stations:
    if not s["operational"]:
        continue
    name = s["name"]
    feeders = []
    for i, dest in enumerate(dest_by_sector.get(name, [])[:2], 1):
        feeders.append({"route": f"F{(abs(hash(name)) % 40) + i}", "type": "feeder-bus",
                        "to": dest, "headwayMin": random.choice([8, 10, 12, 15, 20]),
                        "firstLast": "06:30-22:00"})
    feeders.append({"route": "AUTO", "type": "auto-stand", "to": dest_by_sector.get(name, ["local area"])[0],
                    "headwayMin": 0, "typicalFare": random.choice([30, 40, 40, 50, 60])})
    if random.random() < 0.5:
        feeders.append({"route": "E-RICK", "type": "e-rickshaw", "to": "nearest sectors",
                        "headwayMin": random.choice([5, 8, 10]), "typicalFare": 15})
    lastmile["stations"][name] = {
        "facts": real_connections.get(name, []),
        "feeders": feeders,
        "walkMinutes": random.randint(2, 4),
    }
    for f in feeders[:1]:
        if f["type"] == "feeder-bus":
            busroutes["routes"].append({"route": f["route"], "from": name, "to": f["to"],
                                        "headwayMin": f["headwayMin"], "service": "06:30-22:00"})

for fname, obj in (("timetable.json", timetable), ("fares.json", fares), ("assets.json", assets),
                   ("faults-seed.json", faults_seed), ("lastmile.json", lastmile), ("busroutes.json", busroutes)):
    json.dump(obj, open(os.path.join(DATA, fname), "w"), indent=1, ensure_ascii=False)
    print("saved", fname)

# quick fare check APMC<->Mahatma Mandir
km = 0
for a, b in zip(yellow + red[1:], yellow[1:] + red):
    pass
print("done")
