package dev.mihir.fariyadnative;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import java.util.ArrayList;
import java.util.List;

/** Native SQLite store — the offline source of truth + the sync outbox. */
public class Store extends SQLiteOpenHelper {
    static final class C {
        String id, text, lang, category, engine, severity, team, sla, channel, station, reply;
        int urg; long created; boolean synced;
    }

    private static final String DB = "fariyad.db";

    Store(Context ctx) { super(ctx, DB, null, 1); }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE complaints (" +
            "id TEXT PRIMARY KEY, text TEXT, lang TEXT, category TEXT, engine TEXT," +
            "severity TEXT, urg INTEGER, team TEXT, sla TEXT, channel TEXT, station TEXT," +
            "reply TEXT, synced INTEGER DEFAULT 0, created INTEGER)");
        db.execSQL("CREATE INDEX idx_cat ON complaints(category)");
        db.execSQL("CREATE INDEX idx_created ON complaints(created)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int a, int b) {}

    void insert(C c) {
        ContentValues v = new ContentValues();
        v.put("id", c.id); v.put("text", c.text); v.put("lang", c.lang);
        v.put("category", c.category); v.put("engine", c.engine);
        v.put("severity", c.severity); v.put("urg", c.urg);
        v.put("team", c.team); v.put("sla", c.sla);
        v.put("channel", c.channel); v.put("station", c.station);
        v.put("reply", c.reply); v.put("synced", c.synced ? 1 : 0); v.put("created", c.created);
        getWritableDatabase().insertWithOnConflict("complaints", null, v, SQLiteDatabase.CONFLICT_REPLACE);
    }

    List<C> all() {
        List<C> out = new ArrayList<>();
        try (Cursor cur = getReadableDatabase().query("complaints", null, null, null, null, null, "urg DESC, created DESC")) {
            while (cur.moveToNext()) out.add(row(cur));
        }
        return out;
    }

    List<C> byCategory(String cat) {
        List<C> out = new ArrayList<>();
        try (Cursor cur = getReadableDatabase().query("complaints", null, "category=?",
                new String[]{cat}, null, null, "urg DESC, created DESC")) {
            while (cur.moveToNext()) out.add(row(cur));
        }
        return out;
    }

    int unsynced() {
        try (Cursor cur = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM complaints WHERE synced=0", null)) {
            cur.moveToFirst();
            return cur.getInt(0);
        }
    }

    /** The outbox: every ticket not yet acked by the sync backend. */
    List<C> queuedList() {
        List<C> out = new ArrayList<>();
        try (Cursor cur = getReadableDatabase().query("complaints", null, "synced=0",
                null, null, null, "urg DESC, created DESC")) {
            while (cur.moveToNext()) out.add(row(cur));
        }
        return out;
    }

    /** Flip only the ids the backend actually acked (partial success stays queued). */
    void markSynced(List<String> ids) {
        if (ids == null || ids.isEmpty()) return;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        try {
            ContentValues v = new ContentValues();
            v.put("synced", 1);
            for (String id : ids) db.update("complaints", v, "id=?", new String[]{id});
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    /** Outbox drain (simulated transport — the same envelope contract a GMRC endpoint consumes). */
    int drainOutbox() {
        ContentValues v = new ContentValues();
        v.put("synced", 1);
        return getWritableDatabase().update("complaints", v, "synced=0", null);
    }

    private static C row(Cursor cur) {
        C c = new C();
        c.id = cur.getString(0); c.text = cur.getString(1); c.lang = cur.getString(2);
        c.category = cur.getString(3); c.engine = cur.getString(4); c.severity = cur.getString(5);
        c.urg = cur.getInt(6); c.team = cur.getString(7); c.sla = cur.getString(8);
        c.channel = cur.getString(9); c.station = cur.getString(10); c.reply = cur.getString(11);
        c.synced = cur.getInt(12) == 1; c.created = cur.getLong(13);
        return c;
    }
}
