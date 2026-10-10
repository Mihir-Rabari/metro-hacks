/* ============================================================================
   METRO KIT store — IndexedDB persistence + offline outbox (works in airplane
   mode; queue drains when connectivity returns). Zero dependencies.
   Metro Hacks · Road to DevFest Gandhinagar 2026
   ========================================================================== */
(function (global) {
  'use strict';

  var DB_NAME = 'metrokit';
  var DB_VERSION = 1;
  var STORE = 'records';      // durable fault/ticket records
  var OUTBOX = 'outbox';      // pending sync envelope
  var db = null;
  var listeners = { online: [], offline: [], queued: [], drained: [] };

  function open() {
    return new Promise(function (resolve, reject) {
      if (db) return resolve(db);
      var req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function () {
        var d = req.result;
        if (!d.objectStoreNames.contains(STORE))
          d.createObjectStore(STORE, { keyPath: 'id' });
        if (!d.objectStoreNames.contains(OUTBOX))
          d.createObjectStore(OUTBOX, { keyPath: 'envelopeId', autoIncrement: true });
      };
      req.onsuccess = function () { db = req.result; resolve(db); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function tx(store, mode) {
    return db.transaction(store, mode).objectStore(store);
  }

  function put(store, obj, tries) {
    tries = tries === undefined ? 3 : tries;
    return new Promise(function (resolve, reject) {
      var r;
      try {
        r = tx(store, 'readwrite').put(obj);
      } catch (syncErr) {
        // transaction creation can fail transiently during concurrent drains
        if (tries > 1) { setTimeout(function () { put(store, obj, tries - 1).then(resolve, reject); }, 40); return; }
        console.error('put tx failed', syncErr);
        return reject(syncErr);
      }
      r.onsuccess = function () { resolve(r.result); };
      r.onerror = function () {
        if (tries > 1) { setTimeout(function () { put(store, obj, tries - 1).then(resolve, reject); }, 40); return; }
        reject(r.error);
      };
    });
  }

  function all(store) {
    return new Promise(function (resolve, reject) {
      var r = tx(store, 'readonly').getAll();
      r.onsuccess = function () { resolve(r.result); };
      r.onerror = function () { reject(r.error); };
    });
  }

  function del(store, key) {
    return new Promise(function (resolve, reject) {
      var r = tx(store, 'readwrite').delete(key);
      r.onsuccess = function () { resolve(true); };
      r.onerror = function () { reject(r.error); };
    });
  }

  function count(store) {
    return new Promise(function (resolve, reject) {
      var r = tx(store, 'readonly').count();
      r.onsuccess = function () { resolve(r.result); };
      r.onerror = function () { reject(r.error); };
    });
  }

  /* ------------- public API ------------- */

  // Save a record + enqueue its sync envelope. Works offline by design:
  // the write is local-first; the "server sync" is simulated by the drain
  // below when navigator.onLine returns true.
  function saveRecord(record) {
    record.id = record.id || ('r-' + Date.now() + '-' + Math.floor(Math.random() * 1e6));
    record.savedAt = new Date().toISOString();
    return open().then(function () {
      return put(STORE, record).then(function () {
        // NOTE: envelopeId is omitted — the store's autoIncrement supplies it.
        // An explicit undefined keyPath value throws DataError in Chrome.
        return put(OUTBOX, { recordId: record.id, payload: record,
                             queuedAt: new Date().toISOString() });
      });
    }).then(function () {
      fire('queued');
      attemptDrain();
      return record;
    });
  }

  function allRecords() { return open().then(function () { return all(STORE); }); }

  // Mark everything as synced (simulated ACK from control room)
  function attemptDrain() {
    return open().then(function () {
      return all(OUTBOX).then(function (items) {
        if (!items.length) return 0;
        if (!navigator.onLine) { fire('offline'); return 0; }
        return all(STORE).then(function (records) {
          var byId = {};
          records.forEach(function (r) { byId[r.id] = r; });
          return Promise.all(items.map(function (it) {
            var rec = byId[it.recordId];
            if (rec) { rec.synced = true; rec.syncedAt = new Date().toISOString(); }
            return del(OUTBOX, it.envelopeId).then(function () {
              return rec ? put(STORE, rec) : null;
            });
          })).then(function () {
            fire('drained', items.length);
            return items.length;
          });
        });
      });
    });
  }

  function pendingCount() {
    return open().then(function () { return count(OUTBOX); });
  }

  function fire(evt, data) { (listeners[evt] || []).forEach(function (fn) { fn(data); }); }

  function on(evt, fn) {
    if (!listeners[evt]) listeners[evt] = [];
    listeners[evt].push(fn);
    return function () {
      listeners[evt] = listeners[evt].filter(function (f) { return f !== fn; });
    };
  }

  // wire connectivity events
  window.addEventListener('online', function () { fire('online'); attemptDrain(); });
  window.addEventListener('offline', function () { fire('offline'); });

  global.MetroKit = global.MetroKit || {};
  global.MetroKit.store = {
    saveRecord: saveRecord, allRecords: allRecords, attemptDrain: attemptDrain,
    pendingCount: pendingCount, on: on, open: open,
  };
})(window);
