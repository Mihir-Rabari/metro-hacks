/* ============================================================================
   METRO KIT ai — in-browser inference for models trained offline in Python.
   1) Multinomial naive Bayes (fault triage)     — models/triage.json
   2) CART regression tree (crowding predictor)  — models/crowding.json
   No network, no ML libraries, no compute server. Airplane-mode safe.
   Metro Hacks · Road to DevFest Gandhinagar 2026
   ========================================================================== */
(function (global) {
  'use strict';

  function tokenize(text) {
    var words = String(text).toLowerCase().match(/[a-z0-9]+/g) || [];
    var grams = words.slice();
    for (var i = 0; i < words.length - 1; i++) grams.push(words[i] + '_' + words[i + 1]);
    return grams;
  }

  function nbPredict(weights, tokens) {
    var scores = [];
    for (var label in weights) {
      var w = weights[label];
      var s = w.prior;
      for (var i = 0; i < tokens.length; i++) s += w.llw[tokens[i]] !== undefined ? w.llw[tokens[i]] : Math.log(1e-6);
      scores.push([label, s]);
    }
    scores.sort(function (a, b) { return b[1] - a[1]; });
    var mx = scores[0][1];
    var sum = 0, exps = [];
    for (var j = 0; j < scores.length; j++) { var e = Math.exp(scores[j][1] - mx); exps.push(e); sum += e; }
    return { label: scores[0][0], confidence: exps[0] / sum, ranked: scores.map(function (x) { return { label: x[0], score: x[1] }; }) };
  }

  // Full triage: category + severity + owning team + SLA
  function triage(model, text) {
    var toks = tokenize(text);
    var cat = nbPredict(model.category, toks);
    var sev = nbPredict(model.severity, toks);
    return {
      category: cat.label, categoryConfidence: cat.confidence, categoryRanked: cat.ranked,
      severity: sev.label, team: model.teams[cat.label] || 'Station Manager',
      sla: model.sla[sev.label] || '', text: text,
    };
  }

  // CART regression tree walk
  function treePredict(tree, row) {
    var node = tree;
    while (node.leaf === undefined) {
      node = row[node.f] === node.v ? node.L : node.R;
    }
    return node.leaf;
  }

  // crowding: { stationClass, hour, direction, weekend } -> expected occupancy %
  function crowding(model, opts) {
    var hour = opts.hour, bucket = 'other';
    if (hour >= 6 && hour <= 9) bucket = 'morning_peak';
    else if (hour >= 10 && hour <= 16) bucket = 'midday';
    else if (hour >= 17 && hour <= 20) bucket = 'evening_peak';
    else if (hour >= 21) bucket = 'late';
    var row = { station_class: opts.stationClass, bucket: bucket, direction: opts.direction, weekend: !!opts.weekend };
    var pct = treePredict(model.tree, row);
    // coach-level split: front/mid/rear occupancy varies with boarding pattern
    var coaches = [];
    var pattern = [[-8, 4, 6], [2, 0, 0], [6, -2, -6]][Math.floor(pct / 34)] || [0, 0, 0];
    for (var c = 0; c < 3; c++) {
      coaches.push(Math.max(2, Math.min(99, Math.round(pct + pattern[c]))));
    }
    return { occupancy: Math.round(pct), bucket: bucket, coaches: coaches };
  }

  global.MetroKit = global.MetroKit || {};
  global.MetroKit.ai = { triage: triage, crowding: crowding, treePredict: treePredict, tokenize: tokenize };
})(window);
