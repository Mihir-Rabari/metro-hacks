/* ============================================================================
   METRO KIT map — offline Leaflet wiring: vendored dark tiles from relative
   paths (kit/vendor/leaflet/tiles/{z}/{x}/{y}.png), no network needed.
   Metro Hacks · Road to DevFest Gandhinagar 2026
   ========================================================================== */
(function (global) {
  'use strict';

  var LINE_COLORS = { yellow: '#ffd60a', red: '#ff4d5e', blue: '#4da3ff', violet: '#a78bfa' };

  var FALLBACK_TILE = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

  function tileUrl(pathPrefix, data) {
    if (window.__TILES__) {
      var key = data.z + '/' + data.x + '/' + data.y;
      return window.__TILES__[key] || FALLBACK_TILE;
    }
    return (pathPrefix || '.') + '/vendor/leaflet/tiles/' + data.z + '/' + data.x + '/' + data.y + '.png';
  }

  // L.tileLayer() takes a string pattern; we need per-tile function logic
  // (data-URL lookup in baked builds), so subclass with a custom getTileUrl.
  var OfflineLayer = L.TileLayer.extend({
    getTileUrl: function (coords) {
      return tileUrl(this.options.tilePath, coords);
    },
  });

  function baseMap(elId, opts) {
    opts = opts || {};
    var map = L.map(elId, { zoomControl: true, attributionControl: false, maxZoom: opts.maxZoom || 14, minZoom: 11 });
    var layer = new OfflineLayer({
      maxZoom: 14, minZoom: 11, bounds: [[22.90, 72.42], [23.34, 72.78]],
      errorTileUrl: FALLBACK_TILE, tilePath: opts.tilePath || '..',
    }).addTo(map);
    map.setView(opts.center || [23.10, 72.62], opts.zoom || 11);
    return map;
  }

  function drawLines(map, stations) {
    var layers = {};
    ['yellow', 'red'].forEach(function (line) {
      var pts = stations.filter(function (s) { return s.line === line; })
        .map(function (s) { return [s.lat, s.lon]; });
      layers[line] = L.polyline(pts, {
        color: LINE_COLORS[line], weight: 4, opacity: .85, dashArray: line === 'yellow' ? '' : '8 6',
      }).addTo(map);
    });
    return layers;
  }

  function stationMarkers(map, stations, onPick) {
    markers = {};
    stations.forEach(function (s) {
      if (!s.operational) return;
      var color = LINE_COLORS[s.line];
      var icon = L.divIcon({
        className: 'mk',
        html: '<div style="width:13px;height:13px;border-radius:50%;background:' + color +
              ';box-shadow:0 0 8px ' + color + ';border:2px solid #0a0e14;"></div>',
        iconSize: [17, 17], iconAnchor: [9, 9],
      });
      var m = L.marker([s.lat, s.lon], { icon: icon }).addTo(map);
      m.bindPopup('<b>' + s.name + '</b><br><span style="color:#8b96a9;font-size:12px">' + s.gujarati +
                  '</span><br><span style="font-size:12px;color:#8b96a9">' + s.line.toUpperCase() + ' line · km ' + s.kmFromStart + '</span>');
      if (onPick) m.on('click', function () { onPick(s); });
      markers[s.id] = m;
    });
    return markers;
  }
  var markers;

  global.MetroKit = global.MetroKit || {};
  global.MetroKit.map = { baseMap: baseMap, drawLines: drawLines, stationMarkers: stationMarkers, LINE_COLORS: LINE_COLORS };
})(window);
