package dev.mihir.fariyadnative;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Outbox → backend drain. Plain HttpURLConnection + org.json — zero dependencies.
 * Contract: POST {endpoint}/api/sync with the queued tickets; the server acks
 * ticket ids; only acked ids flip to synced. Unreachable server = tickets stay
 * queued on-device (the offline-first contract — never data loss).
 */
final class Sync {
    /** Default sync endpoint — live tunnel to the Node.js + MongoDB backend
     *  (docker-compose stack in backend/; control-room dashboard at its / page).
     *  Long-press the sync chip in the app to override at runtime. */
    static String DEFAULT_ENDPOINT = "https://adjacent-harper-spare-picture.trycloudflare.com";

    static final class Result {
        boolean reached;
        List<String> acked = new ArrayList<>();
        int queuedCount;
        String error = "";
    }

    static Result drain(String endpoint, List<Store.C> tickets, String deviceId) {
        Result r = new Result();
        r.queuedCount = tickets.size();
        if (tickets.isEmpty()) { r.reached = true; return r; }
        HttpURLConnection c = null;
        try {
            JSONObject body = new JSONObject();
            body.put("deviceId", deviceId);
            JSONArray arr = new JSONArray();
            for (Store.C t : tickets) {
                JSONObject o = new JSONObject();
                o.put("id", t.id);
                o.put("text", t.text);
                o.put("lang", t.lang);
                o.put("category", t.category);
                o.put("engine", t.engine);
                o.put("severity", t.severity);
                o.put("urg", t.urg);
                o.put("team", t.team);
                o.put("sla", t.sla);
                o.put("channel", t.channel);
                o.put("station", t.station);
                o.put("reply", t.reply);
                o.put("created", t.created);
                arr.put(o);
            }
            body.put("tickets", arr);
            byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);

            c = (HttpURLConnection) new URL(endpoint.replaceAll("/+$", "") + "/api/sync").openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setConnectTimeout(5000);
            c.setReadTimeout(10000);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            try (OutputStream os = c.getOutputStream()) { os.write(payload); }

            int code = c.getResponseCode();
            if (code == 200) {
                InputStream in = c.getInputStream();
                byte[] buf = new byte[65536];
                int n; java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                in.close();
                JSONObject res = new JSONObject(bo.toString("UTF-8"));
                JSONArray ack = res.optJSONArray("acked");
                if (ack != null) for (int i = 0; i < ack.length(); i++) r.acked.add(ack.getString(i));
                r.reached = true;
            } else {
                r.error = "HTTP " + code;
            }
        } catch (Exception e) {
            r.error = String.valueOf(e.getMessage());
        } finally {
            if (c != null) c.disconnect();
        }
        return r;
    }
}
