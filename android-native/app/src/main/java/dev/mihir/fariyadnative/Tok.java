package dev.mihir.fariyadnative;

import android.util.JsonReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * XLM-R Unigram (SentencePiece) tokenizer — a hand port of the HF fast tokenizer,
 * verified token-ID-exact against the reference Rust implementation on an 18-sentence
 * multilingual benchmark (Gujarati / Hindi / English / Gujlish / mixed-script).
 *
 * Pipeline (mirrors tokenizer.json):
 *   normalize: NFKC (approximates the precompiled charsmap)
 *   pre-tok :  Sequence[WhitespaceSplit, Metaspace(▁, add_prefix_space)]
 *   model   :  Unigram Viterbi; unknown candidates are PER-CHARACTER with
 *              score = minScore - 10.0 (consecutive unks fused), exactly like
 *              sentencepiece/HF — a whole-word unk candidate is WRONG and
 *              collapses real vocabulary (found the hard way, 8/12 -> 18/18).
 *   wrap    :  <s> ids </s>
 */
final class Tok {
    private final Map<String, Integer> idOf = new HashMap<>(260_000);
    private final List<Float> scoreOf = new ArrayList<>(260_000);
    private float minScore = 0f;
    private final int unkId = 3;
    private final float unkScore;

    private Tok() { unkScore = minScore - 10f; }

    static Tok load(java.io.InputStream in) throws IOException {
        Tok t = new Tok();
        JsonReader r = new JsonReader(new InputStreamReader(in, "UTF-8"));
        r.beginObject();
        while (r.hasNext()) {
            if ("model".equals(r.nextName())) {
                r.beginObject();
                while (r.hasNext()) {
                    String k = r.nextName();
                    if ("vocab".equals(k)) {
                        r.beginArray();
                        while (r.hasNext()) {
                            r.beginArray();
                            String piece = r.nextString();
                            float score = (float) r.nextDouble();
                            t.idOf.put(piece, t.scoreOf.size());
                            t.scoreOf.add(score);
                            r.endArray();
                        }
                        r.endArray();
                    } else if ("unk_id".equals(k)) {
                        r.nextInt();
                    } else {
                        r.skipValue();
                    }
                }
                r.endObject();
            } else {
                r.skipValue();
            }
        }
        r.endObject();
        r.close();
        float mn = 0f;
        for (float s : t.scoreOf) if (s < mn) mn = s;
        t.minScore = mn;
        return t;
    }

    int[] encode(String text) {
        String s = Normalizer.normalize(text == null ? "" : text, Normalizer.Form.NFKC);
        List<Integer> ids = new ArrayList<>(32);
        for (String word : s.trim().split("\\s+")) {
            if (word.isEmpty()) continue;
            viterbi("▁" + word, ids);
        }
        int n = Math.min(ids.size(), 126);          // cap sequence length
        int[] out = new int[n + 2];
        out[0] = 0;                                 // <s>
        for (int i = 0; i < n; i++) out[i + 1] = ids.get(i);
        out[n + 1] = 2;                             // </s>
        return out;
    }

    private void viterbi(String word, List<Integer> out) {
        int n = word.length();
        float[] best = new float[n + 1];
        int[] backI = new int[n + 1];
        int[] backId = new int[n + 1];
        boolean[] seen = new boolean[n + 1];
        best[0] = 0f;
        seen[0] = true;
        for (int i = 0; i < n; i++) {
            if (!seen[i]) continue;
            for (int j = i + 1; j <= n; j++) {
                String piece = word.substring(i, j);
                Integer id = idOf.get(piece);
                float sc;
                int pid;
                if (id != null) {
                    pid = id;
                    sc = scoreOf.get(id);
                } else if (j == i + 1) {
                    pid = unkId;
                    sc = minScore - 10f;
                } else {
                    continue;
                }
                float cand = best[i] + sc;
                if (!seen[j] || cand > best[j]) {
                    best[j] = cand;
                    backI[j] = i;
                    backId[j] = pid;
                    seen[j] = true;
                }
            }
        }
        int[] rev = new int[n];
        int k = n, m = 0;
        while (k > 0) { rev[m++] = backId[k]; k = backI[k]; }
        int prev = -1;
        for (int i = m - 1; i >= 0; i--) {          // reverse + fuse consecutive unks
            if (rev[i] == unkId && prev == unkId) continue;
            out.add(rev[i]);
            prev = rev[i];
        }
    }
}
