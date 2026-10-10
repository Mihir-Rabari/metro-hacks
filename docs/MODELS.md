# 🧠 Fariyad — Model Cards & Evaluation Receipts

Every model in this repo, what it does, where it runs, and what we measured.
No claim below exists without a number behind it — full eval in
[`models/eval.json`](../models/eval.json), reproducible via
[`scripts/eval_neural.py`](../scripts/eval_neural.py).

## Roster

| # | Model | Type | Runs | Size | Latency |
|---|---|---|---|---|---|
| 1 | **fariyad-nb** | Multinomial Naive Bayes (unigram+bigram) | On-device, pure JS | 300 KB JSON | <1 ms |
| 2 | **fariyad-neural** | `Xenova/paraphrase-multilingual-MiniLM-L12-v2`, ONNX q8, centroid head | On-device, WASM (transformers.js) | 118 MB | first call pays one-time graph compilation (seconds); after that a single forward pass |
| 3 | **fariyad-ensemble** | Margin-gated router of 1→2 | On-device | — | sum of both |
| 4 | **crowding tree** | CART regression tree | On-device, JSON tree walk | 4 KB | <0.1 ms (used by `dist/ops.html`) |

Plus two rule-based "models" worth crediting: **script/language detection**
(Gujarati, Devanagari, Latin → gu/hi/en/Gujlish) and the **urgency scorer**
(severity base + hazard keyword lexicon incl. ફસાયા/trapped, suspicious-bag
phrases → S1 = escalate-now, 15-min SLA).

---

## 1 · fariyad-nb — domain engine

- **Task:** complaint text → one of 11 categories (`security_safety`,
  `lifts_escalators`, `afc_gates`, `cleanliness`, `station_infra`,
  `rolling_stock`, `signalling`, `power_traction`, `civic_tickets`,
  `passenger_info`, `staff_behaviour`).
- **Features:** lowercase `[a-z0-9\u0A80-\u0AFF\u0900-\u097F]+` tokens —
  Gujarati, Devanagari and Latin scripts tokenize identically, so **one model
  covers all four input languages**; unigrams + bigrams.
- **Trained on:** 1,248 synthetic GMRC-style complaint phrases written in
  staff-report voice across all four languages. Vocabulary: 2,832.
- **Inference:** in-browser log-likelihood over category priors — the same
  math as training, ported to ~40 lines of JS. Airplane-mode safe.
- **Why it exists:** it knows the *domain* — GMRC assets, departments, failure
  vocabulary — which general-purpose encoders don't.

## 2 · fariyad-neural — the HuggingFace engine

- **Base:** [`Xenova/paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2)
  (ONNX, quantized q8, 118 MB) — distilled multilingual sentence encoder, 384-dim
  embeddings, 50+ languages including Gujarati and Hindi.
- **Why pull instead of train:** no GPU on a moving train, and a 2-hour budget.
  A pretrained multilingual encoder gives Gujarati↔Hindi↔English semantic
  coverage **for free**; we only needed a tiny head on top.
- **Head:** per-category **centroids** — the unit-normalized mean embedding of
  each category's training phrases. Classification = argmax cosine. Trains in
  seconds on CPU, needs zero fine-tuning, exports as 11×384 floats of JSON.
- **Runtime:** transformers.js + ONNX Runtime Web (WASM) inside the same
  single-file app / APK. First inference pays a one-time WASM graph compilation
  (a few seconds on a laptop); after that each triage is a single forward pass.
- **Graceful degradation:** if the model assets are missing (browser build
  offline before caching) the app silently runs NB-only and shows
  `engine: NB` — the neural pill only appears when the graph is actually live
  (`🧠 neural: ON`).

## 3 · fariyad-ensemble — the part that beat both

**Pre-registered rule** (fixed before scoring the holdout): run NB; if NB's
log-likelihood **margin** (top category vs runner-up) is **< 2.0** — i.e. NB's
top pick is not at least ~7.4× more likely than its second pick — NB is
*uncertain*, and the neural opinion wins. Otherwise NB wins.

Why this shape: NB is confidently right in-domain; the transformer knows
phrasings NB has never seen. The rule lets each engine work only where it's
strong, and **both opinions are always rendered as chips** on every complaint —
the ensemble is visible, not magic.

## Held-out evaluation (n = 44, never seen in training)

Complaints written fresh in Gujarati script, Hindi, English, and Gujlish —
not paraphrases of training rows.

| Engine | Accuracy |
|---|---|
| fariyad-nb alone | 79.5% |
| fariyad-neural alone | 70.5% |
| **fariyad-ensemble** | **86.4%** ✅ |

Full per-example log with both engines' predictions and the top cosine for
every miss: [`models/eval.json`](../models/eval.json) → `mismatches`.

### Error analysis — what it gets wrong, honestly

- **Both engines wrong:** *"pickpocket incident at gate"* → both routed to
  `afc_gates` (truth: `security_safety`). "Gate" dominates both signals — a
  classic token-attractor failure.
- **Ensemble over-trusts a confident neural:** *"conductor ne gaali di"*
  (staff abused a passenger) — NB got it right (`staff_behaviour`), neural
  overrode to `rolling_stock` on a strong cosine. Margin rule fired the wrong
  way: NB was uncertain, neural was confidently wrong.
- **Ensemble under-trusts neural:** *"avm me coin nahi lag raha"* — NB said
  `rolling_stock`, neural said `security_safety`, both wrong (truth:
  `afc_gates`); low cosine meant NB's wrong answer stood.
- **Neural rescues (the wins):** *"washroom smells terrible, no water"* —
  NB said `station_infra`, neural correctly overrode to `cleanliness`. This
  pattern — NB unsure on phrasing, neural matching semantics — is where the
  +6.9 points over NB come from.

### What we would do with one more day

Weight the margin gate by neural cosine (don't let a 0.5-cosine override
trump a mildly-confident NB), add a `security_safety` keyword guard for
theft/harassment terms, and grow the holdout to 200+ examples.

## 4 · crowding tree (ops demo)

- **Task:** expected platform occupancy % from (station class, time bucket,
  direction, weekend). **Type:** CART regression tree, 2,200 training rows
  sampled from a synthetic-but-defensible ridership model. **MAE: 7.2** (on
  the synthetic holdout — it's a demo aid for `dist/ops.html`, not a
  production forecast).

## 5 · Provenance statement

Training data is synthetic (no GMRC complaint corpus is public); the eval
holdout was authored **after** models were frozen, and the ensemble rule was
fixed **before** scoring. The neural base model is public and linked above.
Every number on this page is regenerated by one script — nothing is
hand-written.
