#!/usr/bin/env python3
"""Pull a multilingual sentence-transformer from HuggingFace (via fastembed, ONNX)
and benchmark it against our naive-Bayes triage on a HELD-OUT multilingual set.

- Computes per-category centroid embeddings from the training corpus
- Writes centroids for the on-device neural engine (Android bundle + local test)
- Writes models/eval.json with the honest accuracy comparison

Run:  .data/venv/bin/python scripts/eval_neural.py
"""
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CENTROID_OUT = os.path.join(ROOT, "android", "app", "src", "main", "assets", "www", "models", "centroids.json")
EVAL_OUT = os.path.join(ROOT, "models", "eval.json")

# ---------------------------------------------------------------------------
# 1. Load the training corpus (from the committed trainer, no duplication)
# ---------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location("trainer", os.path.join(HERE, "train_triage.py"))
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)
rows = trainer.make_examples()  # [{text, cat, sev}]
texts = [r[0] for r in rows]
cats = [r[1] for r in rows]
print(f"train rows: {len(rows)}")

# ---------------------------------------------------------------------------
# 2. NB scorer from the exported weights (exact browser parity)
# ---------------------------------------------------------------------------
model = json.load(open(os.path.join(ROOT, "models", "triage.json")))

def tokenize(text):
    words = re.findall(r"[a-z0-9\u0A80-\u0AFF\u0900-\u097F]+", text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]

def nb_predict(weights, text, margin=False):
    toks = tokenize(text)
    scores = []
    for label, w in weights.items():
        s = w["prior"]
        for t in toks:
            s += w["llw"].get(t, math.log(1e-6))
        scores.append((label, s))
    scores.sort(key=lambda x: -x[1])
    if margin:
        return scores[0][0], (scores[0][1] - scores[1][1] if len(scores) > 1 else 99)
    return scores[0][0]

# ---------------------------------------------------------------------------
# 3. Held-out evaluation set — fresh phrasings NOT present in training
# ---------------------------------------------------------------------------
HOLDOUT = [
    # lifts_escalators
    ("elevator stopped between floors", "lifts_escalators"), ("સ્ટેશનની લિફ્ટ કામ કરતી નથી", "lifts_escalators"),
    ("escalator ke steps atak rahe hai", "lifts_escalators"), ("the moving staircase is not moving at exit", "lifts_escalators"),
    # afc_gates
    ("fare gate rejecting my ticket repeatedly", "afc_gates"), ("કાર્ડ રીડર મશીન બંધ છે", "afc_gates"),
    ("avm me coin nahi lag raha", "afc_gates"), ("vending machine ate my note no refund", "afc_gates"),
    # cleanliness
    ("floor very dirty near stairs", "cleanliness"), ("સ્ટેશન પર ધૂળ ઘણી છે", "cleanliness"),
    ("gandagi hai platform pe", "cleanliness"), ("washroom smells terrible no water", "cleanliness"),
    # security_safety
    ("someone left a bag unattended", "security_safety"), ("પ્લેટફોર્મ પર શંકાસ્પદ વ્યક્તિ", "security_safety"),
    ("ladki ko paresan kar raha hai koi", "security_safety"), ("pickpocket incident at gate", "security_safety"),
    # staff_behaviour
    ("staff was very arrogant to me", "staff_behaviour"), ("કર્મચારી વર્તન ખરાબ", "staff_behaviour"),
    ("conductor ne gaali di", "staff_behaviour"), ("no one at enquiry window is responding", "staff_behaviour"),
    # station_infra
    ("seepage on the wall platform 2", "station_infra"), ("પ્લેટફોર્મ નં. ૧ ની ટાઇલ ખરડી છે", "station_infra"),
    ("staircase railing tut gayi", "station_infra"), ("ceiling panel hanging platform area", "station_infra"),
    # rolling_stock
    ("coach me ac kaam nahi kar raha", "rolling_stock"), ("ટ્રેનમાં દરવાજા બંધ નથી થતા", "rolling_stock"),
    ("train screeching sound while braking", "rolling_stock"), ("seats torn in second coach", "rolling_stock"),
    # signalling
    ("train atki hui hai signal par", "signalling"), ("red signal par train khadi lambi time", "signalling"),
    ("signal system failure suspected", "signalling"), ("ટ્રેન અચાનક લાલ સિગ્નલ પર ઊભી રહી", "signalling"),
    # power_traction
    ("station lights band ho gayi thi", "power_traction"), ("સ્ટેશનમાં વીજળી ગઈ", "power_traction"),
    ("dg set not starting during power cut", "power_traction"), ("emergency backup not working", "power_traction"),
    # passenger_info
    ("announcement system silent no info", "passenger_info"), ("ડિસ્પ્લે પર માહિતી ખોટી દેખાય છે", "passenger_info"),
    ("wrong side info on display board", "passenger_info"), ("route map banner jala hua hai", "passenger_info"),
    # civic_tickets
    ("auto stand bahut bada traffic jam", "civic_tickets"), ("બહાર રિક્ષા અવરોધ કરે છે", "civic_tickets"),
    ("footpath par rehdi laga hai", "civic_tickets"), ("no parking attendant outside station", "civic_tickets"),
]
print(f"holdout: {len(HOLDOUT)}")

# ---------------------------------------------------------------------------
# 4. Embed with the HF model
# ---------------------------------------------------------------------------
from fastembed import TextEmbedding
import numpy as np

emb_model = TextEmbedding(model_name=MODEL_NAME, cache_dir=os.path.join(ROOT, ".data", "hf-cache"))

def embed_batch(batch):
    return np.array(list(emb_model.embed(batch)))

print("embedding training corpus...")
train_vecs = embed_batch(texts)
print("embedding holdout...")
hold_texts = [h[0] for h in HOLDOUT]
hold_vecs = embed_batch(hold_texts)
# normalize — true cosines live in [-1, 1]
train_norms = np.linalg.norm(train_vecs, axis=1, keepdims=True)
train_vecs = train_vecs / np.maximum(train_norms, 1e-9)
hold_norms = np.linalg.norm(hold_vecs, axis=1, keepdims=True)
hold_vecs = hold_vecs / np.maximum(hold_norms, 1e-9)

# centroids (mean of unit vectors, renormalized)
categories = sorted(set(cats))
centroids = {}
for cat in categories:
    idx = [i for i, c in enumerate(cats) if c == cat]
    v = train_vecs[idx].mean(axis=0)
    v = v / np.linalg.norm(v)
    centroids[cat] = [round(float(x), 6) for x in v]

def cos_centroid(v, cat):
    c = np.array(centroids[cat])
    return float(np.dot(v, c))

# embedder predictions
emb_pred, emb_scores = [], []
for v in hold_vecs:
    sims = [(cat, cos_centroid(v, cat)) for cat in categories]
    sims.sort(key=lambda x: -x[1])
    emb_pred.append(sims[0][0])
    emb_scores.append(sims)

# NB predictions
nb_pred = [nb_predict(model["category"], t) for t in hold_texts]

truth = [h[1] for h in HOLDOUT]
nb_acc = sum(p == t for p, t in zip(nb_pred, truth)) / len(truth)
emb_acc = sum(p == t for p, t in zip(emb_pred, truth)) / len(truth)

# ensemble rule (pre-registered, not tuned on results):
# NB is domain-trained, so it leads. The HF neural engine only takes over when
# NB is genuinely uncertain — top-2 log-likelihood margin < 2.0 (≈ e² = 7.4×
# likelihood ratio). Otherwise its opinion is shown as a second chip.
MARGIN_T = 2.0
ens_pred = []
for t, hold in zip(hold_texts, hold_vecs):
    nb_top, nb_margin = nb_predict(model["category"], t, margin=True)
    sims = sorted(((cat, cos_centroid(hold, cat)) for cat in categories), key=lambda x: -x[1])
    neural_top = sims[0][0]
    ens_pred.append(neural_top if nb_margin < MARGIN_T else nb_top)
ens_acc = sum(p == t for p, t in zip(ens_pred, truth)) / len(truth)

print(f"\nNB accuracy:        {nb_acc:.1%}")
print(f"mMiniLM accuracy:   {emb_acc:.1%}")
print(f"ensemble accuracy:  {ens_acc:.1%}")

mism = [(hold_texts[i], truth[i], nb_pred[i], emb_pred[i], round(emb_scores[i][0][1], 3))
        for i in range(len(truth)) if nb_pred[i] != truth[i] or emb_pred[i] != truth[i]]
print("\nmismatches (text | truth | nb | neural | top-cos):")
for m in mism[:20]:
    print("  ", m)

# ---------------------------------------------------------------------------
# 5. Export centroids + eval report
# ---------------------------------------------------------------------------
os.makedirs(os.path.dirname(CENTROID_OUT), exist_ok=True)
json.dump({
    "meta": {
        "model": "Xenova/paraphrase-multilingual-MiniLM-L12-v2 (ONNX q8, on-device)",
        "method": "per-category centroid of unit-normalized training-phrase embeddings; classify = argmax cosine",
        "dims": len(next(iter(centroids.values()))),
        "generated": "2026-10-10",
    },
    "categories": categories,
    "centroids": centroids,
}, open(CENTROID_OUT, "w"))
print(f"\nsaved {CENTROID_OUT}")

json.dump({
    "meta": {
        "note": "Honest held-out comparison: naive Bayes vs HF multilingual MiniLM (centroid) vs ensemble. "
                "Ensemble rule fixed in advance: neural wins when the NB log-likelihood margin < 2.0 "
                "(i.e. NB's top category is not at least ~7.4x more likely than the runner-up); else NB.",
        "holdoutSize": len(HOLDOUT),
        "model": MODEL_NAME,
    },
    "accuracy": {"nb": round(nb_acc, 4), "neural": round(emb_acc, 4), "ensemble": round(ens_acc, 4)},
    "mismatches": mism,
}, open(EVAL_OUT, "w"), indent=1)
print(f"saved {EVAL_OUT}")
