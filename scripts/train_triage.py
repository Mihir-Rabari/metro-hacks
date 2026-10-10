#!/usr/bin/env python3
"""Train the offline fault-triage model (multinomial naive Bayes, unigrams+bigrams).

Realistic metro staff fault reports (synthetic, GMRC-style) -> category + severity.
Exports compact JSON weights that run in ~40 lines of JS in the browser,
so the AI works with airplane mode ON. No external ML libraries.

Run:  python3 scripts/train_triage.py   ->  models/triage.json
"""
import json
import math
import os
import random
import re
from collections import Counter, defaultdict

random.seed(42)

# ---------------------------------------------------------------------------
# Synthetic training corpus - phrased like real station-staff fault reports.
# ---------------------------------------------------------------------------
CAT = {
    "lifts_escalators": [
        "lift stuck between floors at platform level", "escalator making grinding noise near gate 2",
        "elevator door not closing at concourse", "escalator handrail loose at exit A",
        "lift stopped working passengers trapped", "escalator suddenly stopped running",
        "elevator alarm button not working", "escalator step misaligned at top landing",
        "lift jerking while moving up", "escalator emergency stop button broken",
        "passenger fell on escalator handrail was not moving", "elevator fan not working smell inside lift",
        "escalator comb plate damaged", "lift overload alarm rings even when empty",
    ],
    "afc_gates": [
        "ticket gate not scanning qr code", "afc gate rejects valid card repeatedly",
        "gate barrier stuck half open", "token vending machine out of change",
        "smart card recharge machine screen blank", "gate shows error code e04",
        "afc gate keeps beeping for no reason", "passenger card debited twice at gate",
        "ticket reader at gate 3 not responding", "recharge counter pos machine down",
        "gate flap broken passenger walked through free", "avm machine not accepting notes",
    ],
    "rolling_stock": [
        "train door not closing announcement says path fault", "ac not working in coach 2",
        "train brakes screeching loudly at platform", "coach lights flickering in moving train",
        "train delayed at platform unusual announcement", "pantograph spark seen on third rail",
        "train horn not working", "loose rattling noise under coach floor",
        "door opened between stations", "passenger emergency alarm pulled in coach 3",
        "windshield cracked on incoming train", "interior display showing wrong station name",
    ],
    "signalling": [
        "signal showing red for long time", "track circuit failure reported by control",
        "points not setting at interlocking", "atp warning at crossing signal",
        "train held at red signal 15 minutes", "interlocking panel alarm ringing",
        "axle counter fault on down line", "signal wire loose near mast 14",
        "track bond broken found during inspection", "block section showing occupied when empty",
    ],
    "station_infra": [
        "platform tile cracked near edge", "water dripping from roof on platform 1",
        "drain overflowing at station entrance", "staircase railing loose at exit",
        "pids display showing garbage characters", "station name board faded unreadable",
        "public announcement system distorted", "platform bench broken sharp edges",
        "paint peeling from pillar near stairs", "flood water entering ramp during rain",
        "toilet door broken in gents washroom", "ceiling panel hanging loose at concourse",
    ],
    "power_traction": [
        "third rail power fluctuation reported", "station lights went out for 2 minutes",
        "dg set failed to start during test", "power cable insulation damaged visible",
        "traction substation alarm sounding", "ups not holding charge in equipment room",
        "sparks seen from cable tray near track", "breaker tripping repeatedly feeder panel",
        "transformer oil level low reading", "emergency lighting not switching on",
    ],
    "cleanliness": [
        "platform not swept garbage near dustbin", "washroom flooded water everywhere",
        "spillage of tea on platform floor slippery", "pigeon droppings on staircase seat",
        "dustbin overflowing since morning", "gutka stains on new platform wall",
        "cleaning staff absent platform 2 dirty", "vomitting near lift area needs sanitization",
        "station floor sticky needs mopping", "bad smell in unpaid area corner",
    ],
    "security_safety": [
        "unattended bag near ticket counter", "passenger arguing with staff at gate",
        "cctv camera not covering platform end", "lost child at platform 1",
        "crowd gathering beyond yellow line during peak", "drunk passenger disturbing others in coach",
        "camera wire cut at parking area", "frisking door metal detector beeping continuously",
        "stone pelting reported near viaduct pillar", "someone jumped barrier without ticket",
    ],
    "passenger_info": [
        "announcement says wrong station in gujarati", "display shows train going wrong direction",
        "route map banner torn at entrance", "no announcement when train cancelled",
        "signage to exit B missing", "timetable chart outdated at platform",
        "pids not showing next train time", "confusion at interchange no staff to guide",
        "helpline number printed wrong on poster", "platform display shows old date",
    ],
    "civic_tickets": [
        "auto driver refusing to go by meter outside gate", "bus stop shelter broken outside station",
        "potholes on approach road to station", "no lighting on pedestrian footpath outside",
        "encroachment by vendors at station entry", "cycle stand full and locked broken",
        "parking fee collector absent barrier open", "approach road flooding after rain",
        "pedestrian crossing missing near exit", "feeder bus not arriving as per timing",
    ],
    "staff_behaviour": [
        "staff was rude at ticket counter", "employees behaviour very bad at gate",
        "station staff not helping elderly passenger", "security person shouted without reason",
        "counter staff not answering questions", "staff was on phone ignoring passengers",
        "lady staff misbehaved during frisking", "duty manager refused to listen to complaint",
        "staff behaviour arrogant at enquiry window", "guard did not help with lost ticket",
    ],
}

# Free-text modifiers to grow the corpus naturally
PREFIX = ["", "urgent ", "reported by staff ", "again today ", "second time this week ",
          "during morning peak ", "at night shift ", "passenger complaint ", "during inspection ",
          "immediate attention ", "repeated complaint ", "morning shift found "]
SUFFIX = ["", " please send team", " needs repair", " since yesterday", " platform level",
          " passengers facing problem", " kind attention", " asap", " at gandhinagar station",
          " during peak hours", " staff informed control room"]

SEVERITY_HINTS = {
    "S1": ["trapped", "fell", "emergency", "fire", "spark", "door opened between stations",
           "red signal", "power fluctuation", "flood", "unattended bag", "child",
           "safety", "danger", "stuck between floors", "held", "brakes", "axle counter",
           "ફસાયા", "ફસાઈ", "બાળક", "શંકાસ્પદ", "તાત્કાલિક", "ભીડ", "આગ", "पिछा", "बच्चा",
           "trapped che", "fasaya", "bache ko", "suspicious bag", "urgent"],
    "S2": ["not working", "not scanning", "broken", "stopped", "failure", "alarm", "rejected",
           "down", "blank", "rejects", "not responding", "not closing", "screeching", "fault",
           "delayed", "overflowing", "cracked", "loose", "dripping",
           "band", "nathi", "nahi", "kharab", "chalu", "બંધ", "નથી", "ખરાબ", "ટપકે", "ભરાયું",
           "गंदा", "बंद", "खराब"],
}

# Multilingual extension: real Gujarati / Hindi / "Gujlish" complaint phrasing per category
GU_HI = {
    "lifts_escalators": [
        "lift band che platform par", "escalator chalu nathi exit par", "લિફ્ટ બંધ છે",
        "એસ્કલેટર ચાલતું નથી", "લિફ્ટમાં લોકો ફસાયા છે તાત્કાલિક મદદ", "એસ્કલેટરમાં અવાજ આવે છે",
        "लिफ्ट बंद है", "एस्कलेटर चल रहा नहीं", "lift stuck che log andar",
        "escalator par chal raha nahi hai",
    ],
    "afc_gates": [
        "gate par card chaltu nathi", "token machine kharab che", "ગેટ પર કાર્ડ ચાલતું નથી",
        "ટિકિટ મશીન બંધ છે", "ગેટે પૈસા બે વાર કાપ્યા", "રિચાર્જ મશીન ચાલતું નથી",
        "gate card accept nahi karta", "टिकट मशीन खराब है", "machine se paise cut hue do baar",
        "gate par line lambi hai card nahi chal raha",
    ],
    "cleanliness": [
        "platform ganda che", "toilet ma pani bharyu che", "પ્લેટફોર્મ ગંદું છે",
        "શૌચાલયમાં પાણી ભરાયું છે", "કચરાનો ઢગલો પ્લેટફોર્મ પર છે", "સ્ટેશન પર સફાઈ નથી",
        "platform ganda hai", "toilet ganda hai pani bhara hai", "kachara dagra che",
        "स्टेशन पर सफाई नहीं है",
    ],
    "security_safety": [
        "suspicious bag platform par che", "bache ko kho gaya", "શંકાસ્પદ બેગ પ્લેટફોર્મ પર છે",
        "બાળક ખૂટી ગયું", "ભીડ ઘણી છે પીળી લાઇન વટાવી રહી છે", "દારૂ પીતો માણસ ગેટ પર",
        "suspicious bag hai platform par", "भीड़ बहुत है पीली लाइन पार", "shankaspad bag che",
        "मंच पर संदिग्ध बैग",
    ],
    "staff_behaviour": [
        "staff rude hai", "karmachari gusse thay", "સ્ટાફે ખરાબ વર્તન કર્યું",
        "કર્મચારી ગુસ્સે થયા", "ટિકિટ કાઉન્ટર પર કોઈ જવાબ નથી આપતું", "સ્ટાફ મદદ કરતું નથી",
        "ticket counter par jawab nahi detat", "staff ne gaali di", "कर्मचारी ने गाली दी",
        "staff behaviour kharab che counter par",
    ],
    "rolling_stock": [
        "train ni door band nathi thati", "coach ma AC nathi chaltu", "ટ્રેનનો દરવાજો બંધ નથી થતો",
        "કોચમાં એસી ચાલતી નથી", "train me AC nahi chal raha", "coach ke andar light nahi",
        "train ke brakes ki avaz aa rahi", "train delayed che platform par",
    ],
    "signalling": [
        "train red signal par atki che", "signal lal chhe ghana time", "ટ્રેન લાલ સિગ્નલ પર અટકી છે",
        "train 15 min lal signal par khadi", "signal par train atki hui hai",
    ],
    "station_infra": [
        "chhat thi pani tapke che", "platform ni tile tuti che", "છતમાંથી પાણી ટપકે છે",
        "પ્લેટફોર્મની ટાઇલ તૂટી છે", "light nahi jalti station par", "station par divdali nathi",
        "ढकन से पानी टपक रहा", "staircase ni railing dhili che",
    ],
    "power_traction": [
        "station par light gayi gay", "સ્ટેશન પર લાઇટ ગઈ ગઈ", "light 2 minute band thi",
        "equipment room ma UPS charge nathi rakhtu", "station par bijli gayi thi do minute",
    ],
    "passenger_info": [
        "announcement galat station naam bole che", "display par galat info batave che",
        "જાહેરાત ખોટું સ્ટેશનનું નામ બોલે છે", "display par agli train no time nathi batavtu",
        "घोषणा गलत स्टेशन बोल रही", "pids par galat direction batave che",
    ],
    "civic_tickets": [
        "auto driver meter nathi chalavto gate bahar", "station bahar auto line bhari che",
        "ઓટો ડ્રાઇવર મીટર નથી ચલાવતો", "સ્ટેશનની બહાર ઓટોની લાઇન ભરેલી છે",
        "station ke bahar auto gadi jama hai", "parking ma cycle stand tutu che",
    ],
}

def make_examples():
    rows = []
    for cat, templates in CAT.items():
        all_templates = templates + GU_HI.get(cat, [])
        for t in all_templates:
            for _ in range(6):  # variations
                text = random.choice(PREFIX) + t + random.choice(SUFFIX)
                sev = "S3"
                low = text.lower()
                if any(h in low for h in SEVERITY_HINTS["S1"]):
                    sev = "S1"
                elif any(h in low for h in SEVERITY_HINTS["S2"]):
                    sev = "S2"
                rows.append((text, cat, sev))
    random.shuffle(rows)
    return rows

def tokenize(text):
    words = re.findall(r"[a-z0-9\u0A80-\u0AFF\u0900-\u097F]+", text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]

def train(rows, labels):
    vocab = set()
    counts = defaultdict(Counter)
    class_docs = Counter()
    for text, label in zip(rows, labels):
        toks = tokenize(text)
        vocab.update(toks)
        counts[label].update(toks)
        class_docs[label] += 1
    total_docs = sum(class_docs.values())
    V = len(vocab)
    weights = {}
    for label in class_docs:
        prior = math.log(class_docs[label] / total_docs)
        denom = sum(counts[label].values()) + V
        llw = {t: math.log((c + 1) / denom) for t, c in counts[label].items()}
        weights[label] = {"prior": prior, "llw": llw}
    return weights, sorted(vocab)

def predict(weights, vocab, text, alpha=1.0):
    toks = [t for t in tokenize(text) if t in vocab]
    scores = {}
    for label, w in weights.items():
        s = w["prior"] * alpha
        for t in toks:
            s += w["llw"].get(t, math.log(1.0 / 1e6))
        scores[label] = s
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best = ranked[0][0]
    mx = ranked[0][1]
    exps = [math.exp(v - mx) for _, v in ranked]
    conf = exps[0] / sum(exps)
    return best, conf

def main():
    rows = make_examples()
    texts = [r[0] for r in rows]
    cats = [r[1] for r in rows]
    sevs = [r[2] for r in rows]

    w_cat, vocab = train(texts, cats)
    w_sev, vocab_sev = train(texts, sevs)

    # self-check
    correct = sum(1 for t, c in zip(texts, cats) if predict(w_cat, vocab, t)[0] == c)
    print(f"train size={len(rows)}  cat-acc={correct/len(rows):.3f}")

    teams = {
        "lifts_escalators": "Lifts & Escalators (Mechanical)",
        "afc_gates": "AFC / Ticketing Systems",
        "rolling_stock": "Rolling Stock Maintenance",
        "signalling": "Signalling & Telecom (S&T)",
        "station_infra": "Station Civil Maintenance",
        "power_traction": "Traction & Electrical",
        "cleanliness": "Station Housekeeping",
        "security_safety": "Security (CISF/GRP) + Safety",
        "passenger_info": "Station Operations (PIS/Signage)",
        "civic_tickets": "Station Manager (Last-mile liaison)",
        "staff_behaviour": "HR / Station Manager (Staff conduct)",
    }
    sla = {"S1": "IMMEDIATE - control room + on-call crew (15 min)", "S2": "Same shift - maintenance ticket (2 hrs)",
           "S3": "Daily maintenance queue (24 hrs)"}

    model = {
        "meta": {
            "type": "multinomial-naive-bayes",
            "features": "unigrams+bigrams, lowercase, [a-z0-9]+ tokens",
            "trainedOn": "synthetic GMRC-style fault reports (10 categories)",
            "vocabulary": len(vocab),
            "trainExamples": len(rows),
            "note": "Trained offline in Python; inference runs fully in-browser (airplane-mode safe)."
        },
        "category": w_cat,
        "severity": w_sev,
        "teams": teams,
        "sla": sla,
    }
    out = os.path.join(os.path.dirname(__file__), '..', 'models', 'triage.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(model, open(out, 'w'))
    print("saved", out, f"({os.path.getsize(out)/1024:.0f} KB)")

    # quick sanity probes (all languages the brief mentions)
    probes = ["escalator stopped working at platform 2", "lift stuck between ground and concourse passengers inside",
              "gate not accepting my card", "train door problem in coach", "water leaking on platform",
              "લિફ્ટ બંધ છે", "એસ્કલેટર ચાલતું નથી", "પ્લેટફોર્મ ગંદું છે", "શંકાસ્પદ બેગ પ્લેટફોર્મ પર છે",
              "સ્ટાફે ખરાબ વર્તન કર્યું", "lift band che", "platform ganda hai", "staff rude hai counter par",
              "लिफ्ट बंद है", "toilet ma pani bharyu che", "gate par card chaltu nathi"]
    for p in probes:
        c, conf = predict(w_cat, vocab, p)
        s, _ = predict(w_sev, vocab_sev, p)
        print(f"  '{p}' -> {c} ({conf:.0%}) sev={s}")

if __name__ == "__main__":
    main()
