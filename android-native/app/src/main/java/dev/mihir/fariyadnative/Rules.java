package dev.mihir.fariyadnative;

import org.json.JSONObject;
import java.util.Locale;
import java.util.regex.Pattern;

/** Ported rule models: language/script detection, urgency scoring, reply composition. */
final class Rules {
    private static final Pattern GUJLISH = Pattern.compile(
        "\\b(che|chhe|nathi|nahi|chaltu|chalu|band|ganda|kharab|thay|thaya|gaye|gayu|bharyu|bharelu|par|ma|dagra|sev|vartan|gusse|khali|tupu|dhili|tapke)\\b",
        Pattern.CASE_INSENSITIVE);

    static String langDetect(String t) {
        int gu = 0, hi = 0;
        for (int i = 0; i < t.length(); i++) {
            char ch = t.charAt(i);
            if (ch >= 0x0A80 && ch <= 0x0AFF) gu++;
            else if (ch >= 0x0900 && ch <= 0x097F) hi++;
        }
        if (gu > 0 && gu >= hi) return "gu";
        if (hi > 0) return "hi";
        return GUJLISH.matcher(t).find() ? "gu" : "en";
    }

    private static final String[][] BOOSTS = {
        {"trapped", "10"}, {"ફસાયા", "10"}, {"stuck", "5"}, {"child", "10"}, {"બાળક", "10"},
        {"suspicious", "8"}, {"શંકાસ્પદ", "8"}, {"unattended", "10"}, {"fire", "10"}, {"આગ", "10"},
        {"urgent", "6"}, {"તાત્કાલિક", "6"}, {"ભીડ", "5"}, {"crowd", "5"}, {"slippery", "6"},
        {"flood", "8"}, {"rude", "4"},
    };

    static int urgency(String sev, String text) {
        int u = "S1".equals(sev) ? 90 : "S2".equals(sev) ? 60 : 30;
        String low = text == null ? "" : text.toLowerCase(Locale.ROOT);
        for (String[] b : BOOSTS) if (low.contains(b[0])) u += Integer.parseInt(b[1]);
        return Math.max(1, Math.min(100, u));
    }

    private static String pick(JSONObject o, String lang) {
        if (o == null) return "";
        return o.has(lang) ? o.optString(lang, "") : o.optString("en", "");
    }

    /** R = data/replies.json: openers[sev], actions[cat], sla_line, closers (per language). */
    static String composeReply(JSONObject R, String severity, String category, String sla,
                               String lang, String station, String id) {
        StringBuilder sb = new StringBuilder();
        JSONObject openers = R.optJSONObject("openers");
        sb.append(pick(openers == null ? null : openers.optJSONObject(severity), lang)
            .replace("{id}", id)).append('\n');
        JSONObject actions = R.optJSONObject("actions");
        sb.append(pick(actions == null ? null : actions.optJSONObject(category), lang)
            .replace("{station}", station == null || station.isEmpty() ? "the station" : station)).append('\n');
        sb.append(pick(R.optJSONObject("sla_line"), lang).replace("{sla}", sla)).append('\n');
        sb.append(pick(R.optJSONObject("closers"), lang));
        return sb.toString();
    }
}
