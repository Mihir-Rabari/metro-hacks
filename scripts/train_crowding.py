#!/usr/bin/env python3
"""Train the offline crowding predictor (small CART regression tree, pure Python).

Features: hour-bucket, direction, station class, weekday/weekend.
Target: expected platform+coach occupancy %.
Also exports per-station hourly averages for the "coach crowding guide" view.

Run:  python3 scripts/train_crowding.py  ->  models/crowding.json + data/crowding.json
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

random.seed(7)

HOUR_BUCKETS = [(6, 9, "morning_peak"), (10, 16, "midday"), (17, 20, "evening_peak"), (21, 23, "late")]
DIRECTIONS = {"to_apmc": "southbound (toward Ahmedabad/APMC)", "to_mahatma_mandir": "northbound (toward Gandhinagar)"}

STATION_CLASSES = {
    "Motera Stadium": "interchange", "Old High Court": "interchange",
    "APMC": "terminus", "Mahatma Mandir": "terminus",
    "Sachivalaya": "business", "Sector-10A": "business", "Infocity": "business",
    "Sector-1": "institutional", "GNLU": "institutional", "Dholakuva Circle": "institutional",
    "Gandhigram": "business", "Usmanpura": "business", "Vadaj": "business", "Vijay Nagar": "residential",
    "Randesan": "residential", "Raysan": "residential", "Koba Circle": "residential",
    "Juna Koba": "residential", "Koba Gam": "residential", "Narmada Canal": "residential",
    "Tapovan Circle": "residential", "Vishwakarma College": "institutional", "Koteshwar Road": "residential",
    "Sabarmati": "mixed", "AEC": "mixed", "Ranip": "residential", "Paldi": "mixed",
    "Shreyas": "mixed", "Rajiv Nagar": "residential", "Jivraj Park": "mixed",
    "Sector-16": "institutional", "Sector-24": "residential", "Juna Sachivalaya": "institutional",
    "Akshardham": "institutional", "Sabarmati Railway Station": "mixed",
}

BASE = {"interchange": 42, "terminus": 38, "business": 30, "institutional": 26, "residential": 22, "mixed": 28}

def expected_occupancy(station, hour, direction, is_weekend):
    klass = STATION_CLASSES.get(station, "residential")
    base = BASE[klass]
    bucket = "other"
    for lo, hi, name in HOUR_BUCKETS:
        if lo <= hour <= hi:
            bucket = name
            break
    delta = 0.0
    # Peak-of-peaks: Gandhinagar residential boarding toward Ahmedabad in the morning
    if bucket == "morning_peak":
        delta += 30 if direction == "to_apmc" else 18
        if klass in ("residential", "institutional") and direction == "to_apmc":
            delta += 8
        if klass == "business" and direction == "to_mahatma_mandir":
            delta += 6
    elif bucket == "evening_peak":
        delta += 32 if direction == "to_mahatma_mandir" else 16
        if klass in ("residential", "institutional") and direction == "to_mahatma_mandir":
            delta += 8
        if klass == "business" and direction == "to_apmc":
            delta += 6
    elif bucket == "midday":
        delta += 12 if klass == "interchange" else (6 if klass == "business" else 2)
    elif bucket == "late":
        delta -= 12 if klass in ("institutional", "residential") else 6
    if klass == "interchange":
        delta += 12
    if is_weekend:
        delta -= 10
        if klass in ("institutional", "business"):
            delta -= 14
    return max(4.0, min(98.0, base + delta + random.gauss(0, 5))), bucket

def build_rows():
    stations = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "stations.json")))["stations"]
    route = [s["name"] for s in stations if s["line"] == "yellow"] + \
            [s["name"] for s in stations if s["line"] == "red" and s["name"] != "Motera Stadium"]
    rows, profiles = [], {n: {str(h): [] for h in range(6, 24)} for n in route}
    for _ in range(2600):
        station = random.choice(route)
        hour = random.randint(6, 23)
        direction = random.choice(list(DIRECTIONS))
        is_weekend = random.random() < 0.28
        occ, bucket = expected_occupancy(station, hour, direction, is_weekend)
        rows.append({"station_class": STATION_CLASSES.get(station, "residential"),
                     "bucket": bucket, "direction": direction, "weekend": is_weekend, "occ": occ})
        profiles[station][str(hour)].append(round(occ))
    return rows, profiles

# ------------------------- tiny CART regression -----------------------------
def gini_split(rows):
    best = None
    for feat in ("station_class", "bucket", "direction", "weekend"):
        values = sorted({r[feat] for r in rows})
        for v in values:
            left = [r for r in rows if r[feat] == v]
            right = [r for r in rows if r[feat] != v]
            if len(left) < 25 or len(right) < 25:
                continue
            gain = var(rows) - (len(left) / len(rows)) * var(left) - (len(right) / len(rows)) * var(right)
            if best is None or gain > best[0]:
                best = (gain, feat, v)
    return best

def var(rows):
    mu = sum(r["occ"] for r in rows) / len(rows)
    return sum((r["occ"] - mu) ** 2 for r in rows) / len(rows)

def mean_leaf(rows):
    return round(sum(r["occ"] for r in rows) / len(rows), 1)

def build_tree(rows, depth=0, max_depth=4):
    if depth >= max_depth or len(rows) < 50:
        return {"leaf": mean_leaf(rows), "n": len(rows)}
    split = gini_split(rows)
    if not split or split[0] < 1.0:
        return {"leaf": mean_leaf(rows), "n": len(rows)}
    _, feat, v = split
    left = [r for r in rows if r[feat] == v]
    right = [r for r in rows if r[feat] != v]
    return {"f": feat, "v": v,
            "L": build_tree(left, depth + 1, max_depth),
            "R": build_tree(right, depth + 1, max_depth)}

def tree_predict(tree, row):
    node = tree
    while "leaf" not in node:
        node = node["L"] if row.get(node["f"]) == node["v"] else node["R"]
    return node["leaf"]

def main():
    rows, profiles = build_rows()
    # holdout for honest reporting
    random.shuffle(rows)
    hold = rows[:400]
    train = rows[400:]
    tree = build_tree(train)
    errs = [abs(tree_predict(tree, r) - r["occ"]) for r in hold]
    print(f"rows={len(rows)} tree-depth<=4  holdout MAE={sum(errs)/len(errs):.1f} occupancy points")

    model = {
        "meta": {"type": "cart-regression-tree", "features": ["station_class", "bucket", "direction", "weekend"],
                 "target": "expected occupancy %", "trainExamples": len(train),
                 "note": "Trained offline in pure Python; inference is a JSON tree walk in the browser (airplane-mode safe)."},
        "tree": tree,
        "classes": sorted(set(STATION_CLASSES.values())),
        "directions": DIRECTIONS,
    }
    here = os.path.dirname(__file__)
    os.makedirs(os.path.join(here, "..", "models"), exist_ok=True)
    json.dump(model, open(os.path.join(here, "..", "models", "crowding.json"), "w"), indent=1)
    print("saved models/crowding.json")

    prof_out = {}
    for station, hours in profiles.items():
        prof_out[station] = {h: round(sum(v) / len(v)) for h, v in hours.items() if v}
    json.dump({"meta": {"note": "Synthetic expectation profiles (see assumptions.md); mean expected occupancy per hour.",
                        "source": "trained crowding model aggregate"},
               "stations": prof_out},
              open(os.path.join(here, "..", "data", "crowding.json"), "w"), indent=1)
    print("saved data/crowding.json")

    # sample inference checks
    for station, hour, d in [("Raysan", 8, "to_apmc"), ("Old High Court", 18, "to_mahatma_mandir"),
                             ("Sector-24", 13, "to_apmc")]:
        occ, bucket = expected_occupancy(station, hour, d, False)
        row = {"station_class": STATION_CLASSES[station], "bucket": bucket, "direction": d, "weekend": False}
        print(f"  {station} {hour}:00 {d[:12]:12} -> model {tree_predict(tree, row)}% (generative {occ:.0f}%)")

if __name__ == "__main__":
    main()
