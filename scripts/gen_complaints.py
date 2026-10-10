#!/usr/bin/env python3
"""Generate a mixed-language seeded complaint history (30 days) for the PS-07 app.
Mix of Gujarati script, Hindi, Gujlish/Hinglish (Latin), and English — mirroring
the channels described in PS-07.

Run: python3 scripts/gen_complaints.py -> data/complaints-seed.json
"""
import datetime
import json
import os
import random

random.seed(10726)

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")

POOL = {
    "lifts_escalators": ("Lifts & Escalators", [
        ("લિફ્ટ બંધ છે છેલ્લા અઠવાડિયાથી", "S2"), ("escalator stopped at exit A since morning", "S2"),
        ("લિફ્ટમાં લોકો ફસાયા છે", "S1"), ("lift band che station par", "S2"),
        ("एस्कलेटर चल रहा नहीं था", "S2"), ("escalator handrail loose near gate 2", "S2"),
        ("એસ્કલેટરમાં અવાજ આવે છે", "S3"), ("lift jerking while going up", "S2"),
    ]),
    "afc_gates": ("AFC / Ticketing", [
        ("gate par card chaltu nathi", "S2"), ("ગેટે પૈસા બે વાર કાપ્યા", "S3"),
        ("ticket machine out of change", "S2"), ("ટિકિટ મશીન બંધ છે", "S2"),
        ("gate not scanning my QR code", "S2"), ("टोकन मशीन खराब है", "S2"),
        ("recharge counter par line ghani che", "S3"),
    ]),
    "cleanliness": ("Housekeeping", [
        ("પ્લેટફોર્મ ગંદું છે સવારથી", "S3"), ("toilet ma pani bharyu che", "S2"),
        ("platform ganda hai subah se", "S3"), ("શૌચાલયમાં પાણી ભરાયું છે", "S2"),
        ("kachara dagra che platform par", "S3"), ("spillage near gate, floor slippery", "S2"),
        ("स्टेशन पर सफाई नहीं है", "S3"), ("કચરાનો ઢગલો છે", "S3"),
    ]),
    "security_safety": ("Security & Safety", [
        ("શંકાસ્પદ બેગ પ્લેટફોર્મ પર છે", "S1"), ("unattended bag near ticket counter", "S1"),
        ("bache ko kho gaya platform par", "S1"), ("ભીડ ઘણી છે પીળી લાઇન વટાવી રહી છે", "S1"),
        ("suspicious person loitering at gate", "S1"), ("drunk person disturbing passengers in coach", "S1"),
    ]),
    "staff_behaviour": ("Staff Conduct", [
        ("staff rude hai ticket counter par", "S2"), ("કર્મચારી ગુસ્સે થયા વિના કારણે", "S2"),
        ("counter staff not answering questions", "S3"), ("સ્ટાફ મદદ કરતું નથી", "S2"),
        ("security person shouted at me", "S2"), ("कर्मचारी ने गाली दी", "S2"),
    ]),
    "station_infra": ("Station Civil", [
        ("છતમાંથી પાણી ટપકે છે", "S2"), ("platform tile cracked near edge", "S2"),
        ("staircase railing dhili che", "S2"), ("roof dripping water on platform 1", "S2"),
        ("divdali nathi jalti exit par", "S3"), ("name board faded unreadable", "S3"),
    ]),
    "rolling_stock": ("Rolling Stock", [
        ("coach ma AC nathi chaltu", "S2"), ("train door not closing in coach 2", "S1"),
        ("AC not working in coach 3 since Thaltej", "S2"), ("ટ્રેનનો દરવાજો બંધ નથી થતો", "S1"),
        ("coach lights flickering", "S3"),
    ]),
    "passenger_info": ("Station Ops (PIS)", [
        ("announcement galat station bole che", "S3"), ("display showing wrong next train time", "S3"),
        ("જાહેરાત ખોટું નામ બોલે છે", "S3"), ("exit signage missing to gate B", "S3"),
        ("pids par galat direction che", "S3"),
    ]),
    "civic_tickets": ("Last-mile liaison", [
        ("auto driver meter nathi chalavto", "S3"), ("સ્ટેશનની બહાર ઓટોની લાઇન ભરેલી છે", "S3"),
        ("vendors encroaching at station entry", "S3"), ("approach road potholes after rain", "S3"),
        ("station ke bahar auto jama hai", "S3"),
    ]),
    "power_traction": ("Electrical", [
        ("station par light 2 minute band thi", "S2"), ("ups not holding charge in equipment room", "S2"),
        ("સ્ટેશન પર લાઇટ ગઈ ગઈ", "S2"), ("emergency lighting not switching on", "S1"),
    ]),
    "signalling": ("Signalling (S&T)", [
        ("train red signal par 15 min khadi rahi", "S1"), ("train held at red signal long time", "S1"),
        ("signal fault reported by control", "S1"),
    ]),
}

CHANNELS = ["metro app", "WhatsApp helpline", "email", "paper form (station box)", "Twitter/X DM", "call center"]
NAMES = ["Meera Patel", "Rahul Shah", "Jaydeep Chauhan", "Anjali Desai", "Vikram Solanki", "Priya Trivedi",
         "Harsh Mehta", "Kiran Joshi", "દિપક પટેલ", "રીના શાહ", "Rameshbhai", "કિરણ ઠાકર"]

stations = json.load(open(os.path.join(DATA, "stations.json")))["stations"]
op_stations = [s["name"] for s in stations if s["operational"] and s["line"] == "yellow"]

now = datetime.datetime(2026, 10, 10, 12, 0)
out = []
for i in range(150):
    cat = random.choice(list(POOL))
    dept, texts = POOL[cat]
    text, sev = random.choice(texts)
    ts = now - datetime.timedelta(days=random.randint(0, 30), hours=random.randint(0, 22), minutes=random.randint(0, 59))
    status = random.choices(["resolved", "assigned", "open"], weights=[60, 22, 18])[0]
    out.append({
        "id": f"GM-{2000+i}", "ts": ts.strftime("%Y-%m-%dT%H:%M"), "station": random.choice(op_stations),
        "text": text, "category": cat, "dept": dept, "severity": sev, "status": status,
        "channel": random.choice(CHANNELS), "name": random.choice(NAMES),
    })
out.sort(key=lambda f: f["ts"], reverse=True)
json.dump({"meta": {"note": "Seeded mixed-language complaint history (30 days, 150 entries) for demo + warm queues; see assumptions.md"},
           "complaints": out},
          open(os.path.join(DATA, "complaints-seed.json"), "w"), indent=1, ensure_ascii=False)
langs = sum(1 for c in out if any('\u0A80' <= ch <= '\u0AFF' for ch in c['text']))
hindi = sum(1 for c in out if any('\u0900' <= ch <= '\u097F' for ch in c['text']))
print(f"saved complaints-seed.json: {len(out)} entries | Gujarati-script: {langs} | Hindi-script: {hindi} | rest: Latin/Gujlish")
