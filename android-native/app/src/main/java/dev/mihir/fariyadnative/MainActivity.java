package dev.mihir.fariyadnative;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.IntentFilter;
import android.content.BroadcastReceiver;
import android.net.ConnectivityManager;
import android.os.Bundle;
import android.os.Handler;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Fariyad — native Android grievance triage console (PS-07, Metro Hacks 2026).
 * No WebView. No framework. Framework widgets + SQLite + on-device AI.
 */
public class MainActivity extends Activity {

    private Store store;
    private final Neural neural = new Neural();
    private JSONObject triageModel, replies;
    private final List<String> stations = new ArrayList<>();
    private final List<String> channels = new ArrayList<>();

    private EditText input;
    private TextView triageLive, replyBox, chipEngine, chipSync, chipNet;
    private TextView kpiTotal, kpiOpen, kpiS1, kpiUrg;
    private ScrollView viewIntake;
    private View viewQueues, viewHist;
    private ListView queuesList, histList;
    private Spinner stationSpin, channelSpin;
    private final Handler ui = new Handler();
    private final ExecutorService bg = Executors.newSingleThreadExecutor();
    private Runnable pendingTriage;
    private volatile boolean assetsReady = false;
    private final Random rnd = new Random();

    private static final double MARGIN_T = 2.0; // pre-registered ensemble rule (eval_neural.py)
    private static final String[] LANG_NAME = {"gu:ગુજરાતી", "hi:हिंदी", "en:EN"};

    // ---------------------------------------------------------------- lifecycle
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        reportPreviousCrashIfAny();
        try {
        setContentView(R.layout.activity_main);
        store = new Store(this);

        input = findViewById(R.id.input);
        triageLive = findViewById(R.id.triage_live);
        replyBox = findViewById(R.id.reply_box);
        chipEngine = findViewById(R.id.chip_engine);
        chipSync = findViewById(R.id.chip_sync);
        chipNet = findViewById(R.id.chip_net);
        kpiTotal = findViewById(R.id.kpi_total);
        kpiOpen = findViewById(R.id.kpi_open);
        kpiS1 = findViewById(R.id.kpi_s1);
        kpiUrg = findViewById(R.id.kpi_urg);
        viewIntake = findViewById(R.id.view_intake);
        viewQueues = findViewById(R.id.view_queues);
        viewHist = findViewById(R.id.view_hist);
        queuesList = findViewById(R.id.view_queues);
        histList = findViewById(R.id.hist_list);
        stationSpin = findViewById(R.id.station);
        channelSpin = findViewById(R.id.channel);

        channels.add("metro app"); channels.add("helpline");
        channels.add("social media"); channels.add("paper form"); channels.add("email");

        findViewById(R.id.tab_intake).setOnClickListener(v -> setTab(0));
        findViewById(R.id.tab_queues).setOnClickListener(v -> setTab(1));
        findViewById(R.id.tab_hist).setOnClickListener(v -> setTab(2));
        findViewById(R.id.file_btn).setOnClickListener(v -> fileComplaint());
        findViewById(R.id.sync_btn).setOnClickListener(v -> attemptSync());
        setTab(0);

        input.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int c, int d) {}
            public void onTextChanged(CharSequence s, int a, int b, int c) {}
            public void afterTextChanged(Editable s) { scheduleLiveTriage(); }
        });

        replyBox.setOnLongClickListener(v -> { copyReply(); return true; });

        loadAssetsInBackground();

        // AI init deferred: the UI is usable instantly; models warm up right after
        ui.postDelayed(() -> neural.loadInBackground(this, (ok, why) -> {
            chipEngine.setText(ok ? "🧠 neural: ON" : "engine: NB");
            chipEngine.setTextColor(ok ? 0xFF3DDC84 : 0xFF8B96A8);
            Toast.makeText(this, ok ? "Multilingual neural engine ready (on-device)"
                    : "Neural engine unavailable — NB-only (" + why + ")",
                    Toast.LENGTH_LONG).show();
        }), 2000);

        } catch (Throwable t) { showCrash(t); }
    }

    // ---------------------------------------------------------------- crash capture
    /** Writes + shows any failure that escapes onCreate's try — a screenshot of this
     *  dialog pinpoints the cause without adb. */
    private void showCrash(Throwable t) {
        try {
            java.io.File f = new java.io.File(getFilesDir(), App.CRASH_LOG);
            java.io.PrintWriter w = new java.io.PrintWriter(new java.io.FileWriter(f, true));
            w.println("==== onCreate " + new java.util.Date());
            t.printStackTrace(w);
            w.close();
        } catch (Throwable ignored) { }
        try {
            StringBuilder sb = new StringBuilder(String.valueOf(t));
            for (StackTraceElement el : t.getStackTrace()) sb.append("\n  at ").append(el);
            new AlertDialog.Builder(this)
                    .setTitle("Something failed — screenshot this")
                    .setMessage(sb)
                    .setPositiveButton("Close", null).show();
        } catch (Throwable ignored) { }
    }

    /** If the previous run crashed (killed by App's uncaught handler), show that log now. */
    private void reportPreviousCrashIfAny() {
        try {
            java.io.File f = new java.io.File(getFilesDir(), App.CRASH_LOG);
            if (f.exists()) {
                byte[] buf = new byte[(int) Math.min(f.length(), 8000)];
                java.io.FileInputStream in = new java.io.FileInputStream(f);
                int r = in.read(buf);
                in.close();
                f.delete();
                new AlertDialog.Builder(this)
                        .setTitle("Previous crash log (send a screenshot of this)")
                        .setMessage(new String(buf, 0, Math.max(r, 0), "UTF-8"))
                        .setPositiveButton("OK", null).show();
            }
        } catch (Throwable ignored) { }
    }

    @Override
    protected void onStart() {
        super.onStart();
        registerReceiver(netReceiver, new IntentFilter(ConnectivityManager.CONNECTIVITY_ACTION));
        netUI();
    }

    @Override
    protected void onStop() {
        super.onStop();
        try { unregisterReceiver(netReceiver); } catch (Exception ignored) {}
    }

    private final BroadcastReceiver netReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context c, android.content.Intent i) {
            netUI();
            if (isOnline() && store.unsynced() > 0) {   // train reached a station
                int n = store.drainOutbox();
                toast("📶 connectivity returned — outbox drained: " + n + " ticket(s) synced");
            }
            refresh();
        }
    };

    private boolean isOnline() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        return cm != null && cm.getActiveNetworkInfo() != null && cm.getActiveNetworkInfo().isConnected();
    }

    private void netUI() {
        chipNet.setText(isOnline()
                ? "📶 online — outbox can drain (syncs at stations)"
                : "✈️ No network: complaints still file, triage, queue on-device — nothing is lost");
    }

    // ---------------------------------------------------------------- assets
    private void loadAssetsInBackground() {
        bg.execute(() -> {
            try {
                triageModel = new JSONObject(readAsset("models/triage.json"));
                replies = new JSONObject(readAsset("models/replies.json"));
                JSONObject sj = new JSONObject(readAsset("models/stations.json"));
                JSONArray arr = sj.getJSONArray("stations");
                synchronized (stations) {
                    stations.clear();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject s = arr.getJSONObject(i);
                        if (s.optBoolean("operational", true)) stations.add(s.getString("name"));
                    }
                }
                assetsReady = true;
                ui.post(() -> {
                    ArrayAdapter<String> st = new ArrayAdapter<>(this,
                            android.R.layout.simple_spinner_item,
                            new ArrayList<>(stations));
                    st.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
                    stationSpin.setAdapter(st);
                    ArrayAdapter<String> ch = new ArrayAdapter<>(this,
                            android.R.layout.simple_spinner_item, channels);
                    ch.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
                    channelSpin.setAdapter(ch);
                    refresh();
                });
            } catch (Exception e) {
                ui.post(() -> Toast.makeText(this, "asset load failed: " + e.getMessage(), Toast.LENGTH_LONG).show());
            }
        });
    }

    private String readAsset(String name) throws Exception {
        try (InputStream in = getAssets().open(name)) {
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[1 << 16];
            int r;
            while ((r = in.read(buf)) > 0) bo.write(buf, 0, r);
            return bo.toString("UTF-8");
        }
    }

    // ---------------------------------------------------------------- live triage
    private void scheduleLiveTriage() {
        if (!assetsReady) return;
        if (pendingTriage != null) ui.removeCallbacks(pendingTriage);
        pendingTriage = this::liveTriage;
        ui.postDelayed(pendingTriage, 250);
    }

    private void liveTriage() {
        String text = input.getText().toString().trim();
        if (text.isEmpty()) {
            triageLive.setText("Type a complaint in any language…");
            return;
        }
        bg.execute(() -> {
            Nb.Tri tri = Nb.triage(triageModel, text);
            final String lang = Rules.langDetect(text);
            final int urg = Rules.urgency(tri.severity, text);
            Neural.Out n = neural.isReady() ? neural.classify(text) : null;
            final Nb.Tri t = tri;
            final Neural.Out no = n;
            ui.post(() -> {
                String cat = t.category, engine = "NB";
                if (no != null) {
                    if (t.margin < MARGIN_T) {           // NB genuinely uncertain → neural leads
                        cat = no.category; engine = "neural";
                    } else {
                        engine = no.category.equals(t.category) ? "NB+neural ✓" : "NB (neural 2nd opinion)";
                    }
                }
                String team = triTeam(cat);
                triageLive.setText(team + "\n" + Math.round(t.conf * 100) + "% conf · " + t.severity
                        + " · urgency " + urg + " · " + langName(lang) + "\nengine: " + engine
                        + (no != null ? " (neural: " + no.category + " " + String.format(Locale.US, "%.2f", no.cosine) + ")" : ""));
            });
        });
    }

    private String triTeam(String cat) {
        JSONObject teams = triageModel.optJSONObject("teams");
        return teams != null && teams.has(cat) ? teams.optString(cat, cat) : cat;
    }

    private String langName(String code) {
        for (String l : LANG_NAME) {
            String[] p = l.split(":", 2);
            if (p[0].equals(code)) return p[1];
        }
        return code;
    }

    // ---------------------------------------------------------------- filing
    private void fileComplaint() {
        String text = input.getText().toString().trim();
        if (text.isEmpty()) { toast("Type a complaint first"); return; }
        if (!assetsReady) { toast("Still loading AI assets…"); return; }

        // capture UI state on the main thread before hopping to the worker
        final String station = stationSpin.getSelectedItem() == null ? "Mahatma Mandir" : stationSpin.getSelectedItem().toString();
        final String channel = channelSpin.getSelectedItem() == null ? "metro app" : channelSpin.getSelectedItem().toString();

        bg.execute(() -> {
            Nb.Tri tri = Nb.triage(triageModel, text);
            String lang = Rules.langDetect(text);
            int urg = Rules.urgency(tri.severity, text);
            String cat = tri.category, engine = "NB";
            Neural.Out n = neural.isReady() ? neural.classify(text) : null;
            if (n != null && tri.margin < MARGIN_T) { cat = n.category; engine = "neural"; }
            else if (n != null) engine = n.category.equals(tri.category) ? "NB+neural ✓" : "NB (neural 2nd opinion)";

            String id = "r-" + System.currentTimeMillis() + "-" + (100000 + rnd.nextInt(900000));
            String sla = tri.sla;
            String reply = Rules.composeReply(replies, tri.severity, cat, sla, lang, station, id);

            Store.C c = new Store.C();
            c.id = id; c.text = text; c.lang = lang; c.category = cat; c.engine = engine;
            c.severity = tri.severity; c.urg = urg; c.team = triTeam(cat); c.sla = sla;
            c.channel = channel; c.station = station; c.reply = reply;
            c.created = System.currentTimeMillis();
            c.synced = isOnline();                    // offline → queued in the outbox
            store.insert(c);

            ui.post(() -> {
                input.setText("");
                triageLive.setText("Type a complaint in any language…");
                String head = "✓ Filed " + id + " · " + c.team + " · " + c.severity
                        + " · urgency " + urg + (c.synced ? " · synced" : " · queued (syncs at station)")
                        + "\n\n" + reply
                        + "\n\n(long-press to copy)";
                replyBox.setText(head);
                replyBox.setVisibility(View.VISIBLE);
                refresh();
                toast("Filed ✓ " + id);
            });
        });
    }

    private void copyReply() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm != null) { cm.setPrimaryClip(ClipData.newPlainText("fariyad", replyBox.getText())); toast("Reply copied"); }
    }

    // ---------------------------------------------------------------- tabs, lists, KPIs
    private void setTab(int i) {
        viewIntake.setVisibility(i == 0 ? View.VISIBLE : View.GONE);
        viewQueues.setVisibility(i == 1 ? View.VISIBLE : View.GONE);
        viewHist.setVisibility(i == 2 ? View.VISIBLE : View.GONE);
        refresh();
    }

    private void refresh() {
        bg.execute(() -> {
            List<Store.C> all = store.all();
            int total = all.size();
            int s1 = 0; long urgSum = 0;
            for (Store.C c : all) {
                if ("S1".equals(c.severity)) s1++;
                urgSum += c.urg;
            }
            int unsynced = store.unsynced();
            final Map<String, int[]> byCat = new LinkedHashMap<>();  // cat -> {open, s1, maxUrg}
            for (Store.C c : all) {
                int[] e = byCat.get(c.category);
                if (e == null) { e = new int[]{0, 0, 0}; byCat.put(c.category, e); }
                e[0]++; if ("S1".equals(c.severity)) e[1]++;
                if (c.urg > e[2]) e[2] = c.urg;
            }
            final int fS1 = s1;
            final int fAvgUrg = (total == 0 ? 0 : (int) Math.round(urgSum / (double) total));
            ui.post(() -> {
                kpiTotal.setText(total + "\nfiled");
                kpiOpen.setText(total + "\nopen");
                kpiS1.setText(fS1 + "\nS1 open");
                kpiUrg.setText(fAvgUrg + "\navg urg");
                chipSync.setText("sync " + unsynced);
                renderQueues(byCat);
                renderHistory(all);
            });
        });
    }

    private void renderQueues(Map<String, int[]> byCat) {
        List<String> rows = new ArrayList<>();
        List<String> order = new ArrayList<>(byCat.keySet());
        order.sort((a, b2) -> Integer.compare(byCat.get(b2)[2], byCat.get(a)[2]));   // hottest first
        for (String cat : order) {
            int[] e = byCat.get(cat);
            rows.add(triTeam(cat) + "\n  " + e[0] + " open · S1: " + e[1] + " · top urgency " + e[2]);
        }
        if (rows.isEmpty()) rows.add("No complaints filed yet.\nFile one from the Intake tab — works fully offline.");
        queuesList.setOnItemClickListener((p, v, pos, id2) -> {
            if (order.isEmpty() || pos >= order.size()) return;
            String cat = order.get(pos);
            List<Store.C> tix = store.byCategory(cat);
            List<String> lines = new ArrayList<>();
            for (Store.C c : tix)
                lines.add("[" + c.severity + " · urg " + c.urg + "] " + c.id + (c.synced ? " · synced" : " · queued")
                        + "\n" + c.text + "\n" + langName(c.lang) + " · " + c.engine + " · " + timeAgo(c.created));
            new AlertDialog.Builder(this).setTitle(triTeam(cat))
                    .setItems(lines.toArray(new String[0]), null)
                    .setPositiveButton("Close", null).show();
        });
        queuesList.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, rows));
    }

    private void renderHistory(List<Store.C> all) {
        List<String> rows = new ArrayList<>();
        for (Store.C c : all)
            rows.add(c.id + " · " + c.category + " · urg " + c.urg
                    + (c.synced ? " · synced" : " · QUEUED") + " · " + langName(c.lang)
                    + "\n" + preview(c.text));
        if (rows.isEmpty()) rows.add("Nothing filed yet.");
        histList.setOnItemClickListener((p, v, pos, id2) -> {
            if (pos >= all.size()) return;
            Store.C c = all.get(pos);
            new AlertDialog.Builder(this)
                    .setTitle(c.id + " · " + c.team)
                    .setMessage(c.text + "\n\n" + c.severity + " · urgency " + c.urg + " · " + c.engine
                            + "\nstation: " + c.station + " · channel: " + c.channel
                            + "\n" + (c.synced ? "synced ✓" : "queued — syncs at station")
                            + "\n\nDRAFT REPLY:\n" + c.reply)
                    .setPositiveButton("Close", null)
                    .setNeutralButton("Copy reply", (d, w) -> {
                        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                        if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("fariyad", c.reply));
                        toast("Reply copied");
                    }).show();
        });
        histList.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, rows));
    }

    private void attemptSync() {
        int n = store.drainOutbox();
        toast(n > 0 ? "Outbox drained: " + n + " ticket(s) → synced ✓ (simulated transport, contract-ready)"
                    : "Outbox already empty — everything synced");
        refresh();
    }

    // ---------------------------------------------------------------- small utils
    private String preview(String s) { return s.length() > 60 ? s.substring(0, 60) + "…" : s; }

    private String timeAgo(long t) {
        long s = (System.currentTimeMillis() - t) / 1000;
        if (s < 60) return "just now";
        if (s < 3600) return (s / 60) + "m ago";
        return (s / 3600) + "h ago";
    }

    private void toast(String m) { Toast.makeText(this, m, Toast.LENGTH_SHORT).show(); }
}
