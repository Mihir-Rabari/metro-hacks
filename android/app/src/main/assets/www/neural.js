// ============================================================================
// Fariyad neural engine — Xenova multilingual MiniLM (ONNX q8) running fully
// ON-DEVICE via transformers.js. No network: model + tokenizer are local files.
// Loaded only inside the Android APK bundle (and local http dev); the single-file
// dist silently falls back to the naive Bayes engine.
//
// Ensemble rule (pre-registered in scripts/eval_neural.py, held-out 86.4%):
//   NB is domain-trained and leads. When NB's top-2 log-likelihood margin < 2.0
//   (genuinely uncertain — unseen vocabulary), the neural engine takes over.
//   The neural opinion is ALWAYS shown as a second chip for transparency.
// ============================================================================
const NEURAL = {
  ready: false,
  loading: false,
  engine: 'nb',
  centroids: null,
  categories: null,
  dims: 0,
  extractor: null,

  async load() {
    if (this.ready || this.loading) return this.ready;
    this.loading = true;
    try {
      const mod = await import('./transformers.min.js');
      const pipeline = mod.pipeline;
      const env = mod.env;
      env.allowLocalModels = true;
      env.allowRemoteModels = false;
      env.localModelPath = './'; // transformers.js prefixes this to the model path

      const resp = await fetch('./models/centroids.json');
      const cent = await resp.json();
      this.categories = cent.categories;
      this.centroids = cent.centroids;
      this.dims = cent.meta.dims;

      this.extractor = await pipeline('feature-extraction', './models/multilingual-minilm', { dtype: 'q8' });
      this.ready = true;
      this.engine = 'mminilm-ensemble';
      window.dispatchEvent(new CustomEvent('fariyad-neural-ready'));
      console.log('[fariyad] neural engine ready: multilingual MiniLM on-device');
      return true;
    } catch (e) {
      console.warn('[fariyad] neural engine unavailable — NB-only mode:', e && e.message);
      this.loading = false;
      return false;
    }
  },

  async embed(text) {
    const out = await this.extractor(text, { pooling: 'mean', normalize: true });
    return out.data; // Float32Array, unit-normalized
  },

  async classify(text) {
    const v = await this.embed(text);
    const scored = this.categories.map((cat) => {
      const c = this.centroids[cat];
      let d = 0;
      for (let k = 0; k < this.dims; k++) d += v[k] * c[k];
      return { category: cat, cosine: d };
    }).sort((a, b) => b.cosine - a.cosine);
    return { category: scored[0].category, cosine: scored[0].cosine, ranked: scored };
  },
};

window.FariyadNeural = NEURAL;
NEURAL.load();
