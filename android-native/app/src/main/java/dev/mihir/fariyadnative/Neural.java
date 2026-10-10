package dev.mihir.fariyadnative;

import android.content.Context;
import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.LongBuffer;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The multilingual transformer, running FULLY NATIVE on-device:
 * ONNX Runtime (C++ via JNI) + a hand-ported SentencePiece Unigram tokenizer.
 * Zero JavaScript, zero network. Classifies by cosine to per-category centroids
 * (the same centroids benchmarked in models/eval.json).
 *
 * Load order (background): tokenizer.json -> centroids.json -> copy model.onnx
 * from assets to filesDir -> create OrtSession. Any failure = NB-only mode.
 */
final class Neural {
    interface Listener { void onReady(boolean ok, String why); }

    volatile boolean ready = false;
    private volatile String failWhy = "";
    private Tok tok;
    private OrtEnvironment env;
    private OrtSession session;
    private String[] categories;
    private float[][] centroids;
    private final ExecutorService ex = Executors.newSingleThreadExecutor();

    boolean isReady() { return ready; }
    String failWhy() { return failWhy; }

    void loadInBackground(final Context ctx, final Listener done) {
        ex.execute(() -> {
            try {
                InputStream tjson = ctx.getAssets().open("models/tokenizer.json");
                tok = Tok.load(tjson);
                tjson.close();

                JSONObject cent = new JSONObject(readAll(ctx.getAssets().open("models/centroids.json")));
                JSONArray cats = cent.getJSONArray("categories");
                categories = new String[cats.length()];
                JSONObject cObj = cent.getJSONObject("centroids");
                int dims = cent.getJSONObject("meta").getInt("dims");
                centroids = new float[cats.length()][dims];
                for (int i = 0; i < cats.length(); i++) {
                    categories[i] = cats.getString(i);
                    JSONArray v = cObj.getJSONArray(categories[i]);
                    for (int d = 0; d < dims; d++) centroids[i][d] = (float) v.getDouble(d);
                }

                // copy model out of assets (OrtSession wants a file path)
                File f = new File(ctx.getFilesDir(), "model.onnx");
                if (!f.exists() || f.length() == 0) {
                    try (InputStream in = ctx.getAssets().open("models/model.onnx");
                         FileOutputStream out = new FileOutputStream(f)) {
                        byte[] buf = new byte[1 << 16];
                        int r;
                        while ((r = in.read(buf)) > 0) out.write(buf, 0, r);
                    }
                }

                env = OrtEnvironment.getEnvironment();
                session = env.createSession(f.getAbsolutePath(), new OrtSession.SessionOptions());
                ready = true;
                post(done, true, "mMiniLM on-device");
            } catch (Throwable t) {
                failWhy = String.valueOf(t.getMessage());
                post(done, false, failWhy);
            }
        });
    }

    private void post(final Listener done, final boolean ok, final String why) {
        android.os.Handler h = new android.os.Handler(android.os.Looper.getMainLooper());
        h.post(() -> done.onReady(ok, why));
    }

    static final class Out { String category; float cosine; }

    /** Runs NB-lead ensemble semantics: caller decides via NB margin. */
    synchronized Out classify(String text) {
        if (!ready) return null;
        try {
            int[] ids = tok.encode(text);
            int n = ids.length;
            long[] idArr = new long[n];
            long[] mask = new long[n];
            for (int i = 0; i < n; i++) { idArr[i] = ids[i]; mask[i] = 1L; }

            Map<String, OnnxTensor> inputs = new HashMap<>();
            for (String name : session.getInputNames()) {
                if (name.contains("attention")) {
                    inputs.put(name, OnnxTensor.createTensor(env, LongBuffer.wrap(mask), new long[]{1, n}));
                } else if (name.contains("token_type")) {
                    inputs.put(name, OnnxTensor.createTensor(env, LongBuffer.wrap(new long[n]), new long[]{1, n}));
                } else {
                    inputs.put(name, OnnxTensor.createTensor(env, LongBuffer.wrap(idArr), new long[]{1, n}));
                }
            }
            float[] pooled;
            try (OrtSession.Result res = session.run(inputs)) {
                Object v = res.get(0).getValue();      // float[1][seq][384]
                float[][][] emb = (float[][][]) v;
                int seq = emb[0].length, dims = emb[0][0].length;
                pooled = new float[dims];
                for (int s = 0; s < seq; s++)
                    for (int d = 0; d < dims; d++) pooled[d] += emb[0][s][d];
                for (int d = 0; d < dims; d++) pooled[d] /= seq;   // mean pooling (mask all 1s)
            }
            double norm = 0;
            for (float x : pooled) norm += x * x;
            norm = Math.sqrt(norm);
            if (norm == 0) return null;

            Out best = new Out();
            best.cosine = -2f;
            for (int i = 0; i < categories.length; i++) {
                double dot = 0, cn = 0;
                for (int d = 0; d < pooled.length; d++) { dot += pooled[d] * centroids[i][d]; cn += centroids[i][d] * centroids[i][d]; }
                double cos = dot / (norm * Math.sqrt(cn));
                if (cos > best.cosine) { best.cosine = (float) cos; best.category = categories[i]; }
            }
            return best;
        } catch (Throwable t) {
            return null;
        }
    }

    private static String readAll(InputStream in) throws Exception {
        java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[1 << 16];
        int r;
        while ((r = in.read(buf)) > 0) bo.write(buf, 0, r);
        in.close();
        return bo.toString("UTF-8");
    }
}
