/* ============================================================================
   METRO KIT util — zero-dependency helpers (offline)
   Metro Hacks · Road to DevFest Gandhinagar 2026
   ========================================================================== */
(function (global) {
  'use strict';

  function haversineKm(a, b) {
    var R = 6371;
    var dLat = (b.lat - a.lat) * Math.PI / 180;
    var dLon = (b.lon - a.lon) * Math.PI / 180;
    var la1 = a.lat * Math.PI / 180, la2 = b.lat * Math.PI / 180;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  // service headway by hour (see data/timetable.json meta)
  function headwayMinutes(hour) {
    if ((hour >= 8 && hour <= 11) || (hour >= 17 && hour <= 20)) return 10;
    if ((hour >= 6 && hour <= 7) || (hour >= 12 && hour <= 16)) return 15;
    return 20;
  }

  // fare from km using slab table in data/fares.json
  function fareForKm(km, fares) {
    for (var i = 0; i < fares.slabs.length; i++) {
      if (km <= fares.slabs[i].upToKm) return fares.slabs[i].fare;
    }
    return fares.slabs[fares.slabs.length - 1].fare;
  }

  // route km between two stations on the same ordered line list
  function kmBetween(stations, from, to) {
    var a = -1, b = -1;
    for (var i = 0; i < stations.length; i++) {
      if (stations[i].name === from) a = i;
      if (stations[i].name === to) b = i;
    }
    if (a === -1 || b === -1) return null;
    var lo = Math.min(a, b), hi = Math.max(a, b);
    var d = 0;
    for (var j = lo + 1; j <= hi; j++) d += stations[j].kmFromPrev;
    return Math.round(d * 10) / 10;
  }

  function hhmm(mins) {
    var h = Math.floor(mins / 60), m = Math.round(mins % 60);
    return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
  }

  function parseHM(s) { var p = s.split(':'); return (+p[0]) * 60 + (+p[1]); }

  function nowIST() {
    var d = new Date();
    var utc = d.getTime() + d.getTimezoneOffset() * 60000;
    return new Date(utc + 5.5 * 3600000);
  }

  function crowdLevel(pct) {
    if (pct < 35) return { label: 'Easy', cls: 's3', color: '#3ddc84' };
    if (pct < 60) return { label: 'Moderate', cls: 's2', color: '#ffb340' };
    if (pct < 80) return { label: 'Busy', cls: 's1', color: '#ff8c42' };
    return { label: 'Packed', cls: 's1', color: '#ff4d5e' };
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(null, args); }, ms);
    };
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  global.MetroKit = global.MetroKit || {};
  global.MetroKit.util = {
    haversineKm: haversineKm, headwayMinutes: headwayMinutes, fareForKm: fareForKm,
    kmBetween: kmBetween, hhmm: hhmm, parseHM: parseHM, nowIST: nowIST,
    crowdLevel: crowdLevel, debounce: debounce, el: el,
  };
})(window);
