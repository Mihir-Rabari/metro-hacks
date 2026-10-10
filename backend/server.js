// ============================================================================
// Fariyad sync backend — Node.js + MongoDB (the pilot's "station-side" server).
//
// Contract (mirrors the app's outbox drain):
//   POST /api/sync   { deviceId, tickets: [ { id, text, lang, category, engine,
//                          severity, urg, team, sla, channel, station, reply, created } ] }
//                →  { acked: [ids], failed: [ids], serverTime }
//   GET  /api/tickets?limit=50   → newest tickets first
//   GET  /api/stats              → { total, byDept, s1, avgUrg }
//   GET  /health                 → liveness + mongo status
//
// The app is offline-first: if this server is unreachable, tickets STAY QUEUED
// on the device — that is the design, not a failure mode.
// ============================================================================
const express = require('express');
const { MongoClient } = require('mongodb');
const path = require('path');

const PORT = process.env.PORT || 3000;
const MONGO_URL = process.env.MONGO_URL || 'mongodb://127.0.0.1:27017';
const DB = process.env.MONGO_DB || 'fariyad';

const app = express();
app.use(express.json({ limit: '4mb' }));
app.use(express.static(path.join(__dirname, 'public')));

let db = null;
let coll = null;
let effectiveUrl = MONGO_URL;

// ---- optional embedded mongod (real MongoDB binary, persisted to ./data/mongo).
// Used where no docker daemon is available; docker compose remains the
// canonical frozen stack (see docker-compose.yml).
async function maybeStartEmbeddedMongo() {
  if (process.env.MONGO_EMBEDDED !== '1') return;
  const { MongoMemoryServer } = require('mongodb-memory-server');
  const dbPath = path.join(__dirname, 'data', 'mongo');
  require('fs').mkdirSync(dbPath, { recursive: true });
  const mem = await MongoMemoryServer.create({
    instance: {
      port: parseInt(process.env.MONGO_EMBEDDED_PORT || '27027', 10),
      dbPath,
      storageEngine: 'wiredtiger',
    },
  });
  effectiveUrl = mem.getUri('fariyad').replace(/\/$/, '');
  console.log(`[fariyad] embedded mongod running: ${effectiveUrl}`);
}

// ---- connect with retry (compose starts mongo in parallel) -----------------
async function connectMongo() {
  for (;;) {
    try {
      const client = new MongoClient(effectiveUrl, { serverSelectionTimeoutMS: 4000 });
      await client.connect();
      db = client.db(DB);
      coll = db.collection('complaints');
      await coll.createIndex({ id: 1 }, { unique: true });
      await coll.createIndex({ created: -1 });
      await coll.createIndex({ category: 1 });
      console.log(`[fariyad] mongo connected: ${MONGO_URL} / ${DB}`);
      return;
    } catch (e) {
      console.log(`[fariyad] mongo not ready (${e.message}) — retrying in 3s`);
      await new Promise(r => setTimeout(r, 3000));
    }
  }
}

// ---- API --------------------------------------------------------------------
app.get('/health', (_req, res) => {
  res.json({ ok: true, mongo: !!coll, service: 'fariyad-sync', time: new Date().toISOString() });
});

app.post('/api/sync', async (req, res) => {
  if (!coll) return res.status(503).json({ ok: false, error: 'mongo not ready' });
  const deviceId = (req.body && req.body.deviceId) || 'unknown-device';
  const tickets = (req.body && req.body.tickets) || [];
  if (!Array.isArray(tickets) || tickets.length === 0) {
    return res.json({ ok: true, acked: [], failed: [], serverTime: Date.now() });
  }
  const acked = [];
  const failed = [];
  for (const t of tickets) {
    if (!t || !t.id) { failed.push(t && t.id); continue; }
    try {
      await coll.updateOne(
        { id: t.id },
        { $set: { ...t, deviceId, syncedAt: new Date().toISOString() } },
        { upsert: true }
      );
      acked.push(t.id);
    } catch (e) {
      failed.push(t.id);
    }
  }
  console.log(`[fariyad] sync from ${deviceId}: ${acked.length} acked, ${failed.length} failed`);
  res.json({ ok: failed.length === 0, acked, failed, serverTime: Date.now() });
});

app.get('/api/tickets', async (req, res) => {
  if (!coll) return res.status(503).json({ ok: false, error: 'mongo not ready' });
  const limit = Math.min(parseInt(req.query.limit || '50', 10) || 50, 200);
  const rows = await coll.find({}, { projection: { _id: 0 } })
    .sort({ created: -1 }).limit(limit).toArray();
  res.json({ ok: true, count: rows.length, tickets: rows });
});

app.get('/api/stats', async (_req, res) => {
  if (!coll) return res.status(503).json({ ok: false, error: 'mongo not ready' });
  const total = await coll.countDocuments({});
  const byDept = await coll.aggregate([
    { $group: { _id: '$category', n: { $sum: 1 }, maxUrg: { $max: '$urg' } } },
    { $sort: { n: -1 } }
  ]).toArray();
  const s1 = await coll.countDocuments({ severity: 'S1' });
  const avg = await coll.aggregate([
    { $group: { _id: null, avgUrg: { $avg: '$urg' } } }
  ]).toArray();
  res.json({
    ok: true, total, s1,
    avgUrg: avg.length ? Math.round(avg[0].avgUrg) : 0,
    byDept: byDept.map(d => ({ dept: d._id, n: d.n, maxUrg: d.maxUrg || 0 }))
  });
});

// ---- boot -------------------------------------------------------------------
maybeStartEmbeddedMongo()
  .then(connectMongo)
  .then(() => {
    app.listen(PORT, () => console.log(`[fariyad] sync backend on :${PORT} (dashboard at /)`));
  });
