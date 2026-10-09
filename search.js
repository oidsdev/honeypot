/* Ranked search over skill name, description, and tags. No dependencies.

   Score is the sum of tf * idf across query tokens.
   tf is a weighted count: name 3, tag 2, description 1.
   idf is log((N + 1) / (df + 1)) + 1.
   A query token matches a doc token exactly, or with one insertion,
   deletion, or substitution when the query token is not already in
   the index and both tokens are at least 3 characters. Inexact
   matches count half.
*/
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HoneypotSearch = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var NAME_W = 3;
  var TAG_W = 2;
  var DESC_W = 1;
  var FUZZY = 0.5;
  var MIN_FUZZY = 3;

  function spans(text) {
    var out = [];
    var re = /[a-z0-9]+/g;
    var src = String(text || '').toLowerCase();
    var m;
    while ((m = re.exec(src))) {
      out.push({ tok: m[0], start: m.index, end: m.index + m[0].length });
    }
    return out;
  }

  // True when a and b differ by at most one insert, delete, or substitution.
  function withinOneEdit(a, b) {
    var la = a.length;
    var lb = b.length;
    if (Math.abs(la - lb) > 1) return false;
    if (la > lb) return withinOneEdit(b, a);
    var i = 0;
    var j = 0;
    var used = false;
    while (i < la && j < lb) {
      if (a.charAt(i) === b.charAt(j)) {
        i++;
        j++;
        continue;
      }
      if (used) return false;
      used = true;
      if (la === lb) i++;
      j++;
    }
    return true;
  }

  function addTf(tf, list, w) {
    for (var i = 0; i < list.length; i++) {
      var t = list[i].tok;
      tf[t] = (tf[t] || 0) + w;
    }
  }

  function rangesFor(list, terms) {
    var out = [];
    for (var i = 0; i < list.length; i++) {
      if (terms[list[i].tok]) out.push([list[i].start, list[i].end]);
    }
    return out;
  }

  function rank(skills, query) {
    var docs = (skills || []).map(function (s, i) {
      var nameSpans = spans(s.name);
      var descSpans = spans(s.description);
      var tagSpans = (s.tags || []).map(function (t) { return spans(t); });
      var tf = {};
      addTf(tf, nameSpans, NAME_W);
      addTf(tf, descSpans, DESC_W);
      for (var t = 0; t < tagSpans.length; t++) addTf(tf, tagSpans[t], TAG_W);
      return {
        skill: s,
        index: i,
        tf: tf,
        nameSpans: nameSpans,
        descSpans: descSpans,
        tagSpans: tagSpans
      };
    });

    var df = {};
    for (var d = 0; d < docs.length; d++) {
      var terms = docs[d].tf;
      for (var term in terms) {
        if (Object.prototype.hasOwnProperty.call(terms, term)) df[term] = (df[term] || 0) + 1;
      }
    }
    var n = docs.length || 1;
    function idf(term) {
      return Math.log((n + 1) / ((df[term] || 0) + 1)) + 1;
    }

    var qTokens = [];
    var seen = {};
    var qSpans = spans(query);
    for (var q = 0; q < qSpans.length; q++) {
      var qt = qSpans[q].tok;
      if (!seen[qt]) {
        seen[qt] = true;
        qTokens.push(qt);
      }
    }

    if (!qTokens.length) {
      return docs.map(function (doc) {
        return {
          skill: doc.skill,
          score: 0,
          ranges: {
            name: [],
            description: [],
            tags: doc.tagSpans.map(function () { return []; })
          }
        };
      });
    }

    var hits = [];
    for (var h = 0; h < docs.length; h++) {
      var doc = docs[h];
      var score = 0;
      var matched = {};
      for (var qi = 0; qi < qTokens.length; qi++) {
        var token = qTokens[qi];
        var known = !!df[token];
        var best = 0;
        var bestTerm = null;
        for (var dt in doc.tf) {
          if (!Object.prototype.hasOwnProperty.call(doc.tf, dt)) continue;
          var factor = 0;
          if (dt === token) factor = 1;
          else if (!known && token.length >= MIN_FUZZY && dt.length >= MIN_FUZZY && withinOneEdit(token, dt)) factor = FUZZY;
          if (!factor) continue;
          var s = doc.tf[dt] * idf(dt) * factor;
          if (s > best) {
            best = s;
            bestTerm = dt;
          }
        }
        if (bestTerm) {
          score += best;
          matched[bestTerm] = true;
        }
      }
      if (score <= 0) continue;
      var tagRanges = doc.tagSpans.map(function (list) { return rangesFor(list, matched); });
      var nameRanges = rangesFor(doc.nameSpans, matched);
      var descRanges = rangesFor(doc.descSpans, matched);
      hits.push({
        skill: doc.skill,
        score: score,
        index: doc.index,
        ranges: { name: nameRanges, description: descRanges, tags: tagRanges },
        snippet: snippetOf(doc.skill, nameRanges, descRanges, tagRanges)
      });
    }

    hits.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.index - b.index;
    });
    return hits;
  }

  // Excerpt that contains the hit: description, else name, else matching tags.
  function snippetOf(skill, nameRanges, descRanges, tagRanges) {
    if (descRanges.length) return { text: skill.description || '', ranges: descRanges };
    if (nameRanges.length) return { text: skill.name || '', ranges: nameRanges };
    var text = '';
    var ranges = [];
    var tags = skill.tags || [];
    for (var i = 0; i < tags.length; i++) {
      var rs = tagRanges[i] || [];
      if (!rs.length) continue;
      if (text) text += ' ';
      var base = text.length;
      text += tags[i];
      for (var r = 0; r < rs.length; r++) ranges.push([base + rs[r][0], base + rs[r][1]]);
    }
    return { text: text, ranges: ranges };
  }

  return { rank: rank };
});
