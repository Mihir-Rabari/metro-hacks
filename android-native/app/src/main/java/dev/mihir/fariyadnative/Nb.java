package dev.mihir.fariyadnative;

import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Multinomial naive Bayes triage — a faithful port of kit/ai.js (which mirrors
 * scripts/train_triage.py). Tokenizer regex MUST match the trainer:
 * [a-z0-9\u0A80-\u0AFF\u0900-\u097F]+ (Gujarati + Devanagari + Latin).
 */
final class Nb {
    static final Pattern WORDS = Pattern.compile("[a-z0-9\\u0A80-\\u0AFF\\u0900-\\u097F]+");
    private static final double UNK = Math.log(1e-6);

    static List<String> tokenize(String text) {
        List<String> out = new ArrayList<>();
        Matcher m = WORDS.matcher(text == null ? "" : text.toLowerCase(Locale.ROOT));
        List<String> w = new ArrayList<>();
        while (m.find()) w.add(m.group());
        out.addAll(w);
        for (int i = 0; i < w.size() - 1; i++) out.add(w.get(i) + "_" + w.get(i + 1));
        return out;
    }

    static final class Scored { final String label; final double score;
        Scored(String l, double s) { label = l; score = s; } }

    static final class Pred {
        final String label; final double conf; final List<Scored> ranked;
        Pred(String l, double c, List<Scored> r) { label = l; conf = c; ranked = r; }
        double margin() { return ranked.size() > 1 ? ranked.get(0).score - ranked.get(1).score : 99; }
    }

    /** weights: { label: { prior: double, llw: { token: logp } } } */
    static Pred predict(JSONObject weights, List<String> tokens) {
        List<Scored> scores = new ArrayList<>();
        Iterator<String> it = weights.keys();
        while (it.hasNext()) {
            String label = it.next();
            JSONObject w = weights.optJSONObject(label);
            if (w == null) continue;
            double s = w.optDouble("prior", 0);
            JSONObject llw = w.optJSONObject("llw");
            for (String t : tokens) {
                double v = llw != null && llw.has(t) ? llw.optDouble(t, UNK) : UNK;
                s += v;
            }
            scores.add(new Scored(label, s));
        }
        scores.sort((a, b) -> Double.compare(b.score, a.score));
        double mx = scores.isEmpty() ? 0 : scores.get(0).score;
        double sum = 0;
        for (Scored sc : scores) sum += Math.exp(sc.score - mx);
        double conf = sum > 0 ? Math.exp(scores.get(0).score - mx) / sum : 0;
        return new Pred(scores.get(0).label, conf, scores);
    }

    static final class Tri {
        String category, severity, team, sla;
        double conf; double margin;
    }

    /** model: { category: {...}, severity: {...}, teams: {...}, sla: {...} } */
    static Tri triage(JSONObject model, String text) {
        List<String> toks = tokenize(text);
        Pred cat = predict(model.optJSONObject("category"), toks);
        Pred sev = predict(model.optJSONObject("severity"), toks);
        Tri t = new Tri();
        t.category = cat.label;
        t.conf = cat.conf;
        t.margin = cat.margin();
        t.severity = sev.label;
        JSONObject teams = model.optJSONObject("teams");
        t.team = teams != null && teams.has(cat.label) ? teams.optString(cat.label, "Station Manager") : "Station Manager";
        JSONObject sla = model.optJSONObject("sla");
        t.sla = sla != null && sla.has(sev.label) ? sla.optString(sev.label, "") : "";
        return t;
    }
}
