/* Ranked search over Honeypot skills. No dependencies.

   Tokens are lowercase words. A query token matches a token in the name,
   description, or tags. Exact matches rank above a one-character typo
   (Levenshtein distance 1). Typos apply only to tokens of 4+ characters,
   and only when that query token is not already in the index. The score
   is field-weighted TF-IDF: name, then tags, then description.
*/
(function (root) {
  var FIELD_WEIGHT = { name: 5, tags: 3, description: 1 };
  var FUZZY_FACTOR = 0.5;
  var MIN_FUZZY_LEN = 4;
  var SNIPPET_LIMIT = 200;
  var SNIPPET_RADIUS = 60;
  var STOP = {
    a: 1, an: 1, the: 1, of: 1, to: 1, and: 1, or: 1, for: 1,
    in: 1, on: 1, with: 1, via: 1, from: 1, by: 1
  };

  function tokenize(text) {
    var parts = String(text || '').toLowerCase().split(/[^a-z0-9]+/);
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] && !STOP[parts[i]]) out.push(parts[i]);
    }
    return out;
  }

  function unique(tokens) {
    var seen = {};
    var out = [];
    for (var i = 0; i < tokens.length; i++) {
      if (!seen[tokens[i]]) {
        seen[tokens[i]] = 1;
        out.push(tokens[i]);
      }
    }
    return out;
  }

  function termSet(terms) {
    var set = {};
    for (var i = 0; i < terms.length; i++) set[terms[i]] = 1;
    return set;
  }

  // True when Levenshtein distance is exactly 1. Equal strings are false.
  function oneEdit(a, b) {
    var la = a.length;
    var lb = b.length;
    if (Math.abs(la - lb) > 1 || a === b) return false;
    if (la === lb) {
      var diffs = 0;
      for (var i = 0; i < la; i++) {
        if (a.charAt(i) !== b.charAt(i)) {
          diffs++;
          if (diffs > 1) return false;
        }
      }
      return diffs === 1;
    }
    var s = la < lb ? a : b;
    var l = la < lb ? b : a;
    var i = 0;
    var j = 0;
    var skipped = 0;
    while (i < s.length && j < l.length) {
      if (s.charAt(i) !== l.charAt(j)) {
        skipped++;
        if (skipped > 1) return false;
        j++;
      } else {
        i++;
        j++;
      }
    }
    return true;
  }

  function countTokens(tokens) {
    var tf = {};
    for (var i = 0; i < tokens.length; i++) {
      tf[tokens[i]] = (tf[tokens[i]] || 0) + 1;
    }
    return tf;
  }

  var preparedFor = null;
  var prepared = null;

  function prepare(skills) {
    if (prepared && preparedFor === skills) return prepared;
    var docs = [];
    var df = {};
    for (var i = 0; i < skills.length; i++) {
      var s = skills[i];
      var fields = {
        name: tokenize(s.name),
        description: tokenize(s.description),
        tags: tokenize((s.tags || []).join(' '))
      };
      var tf = {
        name: countTokens(fields.name),
        description: countTokens(fields.description),
        tags: countTokens(fields.tags)
      };
      var seen = {};
      var f;
      for (f in tf) {
        if (!Object.prototype.hasOwnProperty.call(tf, f)) continue;
        for (var term in tf[f]) {
          if (Object.prototype.hasOwnProperty.call(tf[f], term)) seen[term] = 1;
        }
      }
      for (var term in seen) {
        if (Object.prototype.hasOwnProperty.call(seen, term)) {
          df[term] = (df[term] || 0) + 1;
        }
      }
      docs.push({ skill: s, index: i, tf: tf });
    }
    var n = docs.length;
    var idf = {};
    var vocab = [];
    for (var term in df) {
      if (!Object.prototype.hasOwnProperty.call(df, term)) continue;
      idf[term] = Math.log((1 + n) / (1 + df[term])) + 1;
      vocab.push(term);
    }
    preparedFor = skills;
    prepared = { docs: docs, idf: idf, vocab: vocab };
    return prepared;
  }

  // Each query token becomes a list of {term, factor}. Exact wins outright
  // when the token is in the vocabulary; otherwise nearby tokens count half.
  function resolve(token, index) {
    if (index.idf[token]) return [{ term: token, factor: 1 }];
    if (token.length < MIN_FUZZY_LEN) return [];
    var alts = [];
    for (var i = 0; i < index.vocab.length; i++) {
      var v = index.vocab[i];
      if (Math.abs(v.length - token.length) > 1) continue;
      if (oneEdit(token, v)) alts.push({ term: v, factor: FUZZY_FACTOR });
    }
    return alts;
  }

  function altScore(doc, alt, idf) {
    var score = 0;
    var fields = ['name', 'description', 'tags'];
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i];
      var tf = doc.tf[f][alt.term] || 0;
      if (!tf) continue;
      score += FIELD_WEIGHT[f] * (1 + Math.log(tf)) * idf[alt.term] * alt.factor;
    }
    return score;
  }

  function bestAlt(doc, alts, idf) {
    var best = 0;
    var term = '';
    for (var i = 0; i < alts.length; i++) {
      var score = altScore(doc, alts[i], idf);
      if (score > best) {
        best = score;
        term = alts[i].term;
      }
    }
    return { score: best, term: term };
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function splitParts(text) {
    var re = /[A-Za-z0-9]+|[^A-Za-z0-9]+/g;
    var out = [];
    var m;
    while ((m = re.exec(text))) out.push(m[0]);
    return out;
  }

  function isWord(part) {
    return /^[A-Za-z0-9]+$/.test(part);
  }

  function highlight(text, terms) {
    var set = termSet(terms);
    var parts = splitParts(text);
    var html = '';
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      if (isWord(part) && set[part.toLowerCase()]) html += '<mark>' + escapeHtml(part) + '</mark>';
      else html += escapeHtml(part);
    }
    return html;
  }

  // Full description when it is short. A window around the first hit when it is not.
  function descriptionSnippet(text, terms) {
    var raw = String(text || '');
    var parts = splitParts(raw);
    var set = termSet(terms);
    var starts = [];
    var pos = 0;
    var hit = -1;
    for (var i = 0; i < parts.length; i++) {
      starts.push(pos);
      if (hit < 0 && isWord(parts[i]) && set[parts[i].toLowerCase()]) hit = i;
      pos += parts[i].length;
    }
    if (hit < 0) return { html: escapeHtml(raw), hit: false };
    if (raw.length <= SNIPPET_LIMIT) return { html: highlight(raw, terms), hit: true };
    var hitPos = starts[hit];
    var hitEnd = hitPos + parts[hit].length;
    var start = hit;
    while (start > 0 && hitPos - starts[start - 1] <= SNIPPET_RADIUS) start--;
    var end = hit + 1;
    while (end < parts.length && (starts[end] + parts[end].length) - hitEnd <= SNIPPET_RADIUS) end++;
    var slice = parts.slice(start, end).join('').trim();
    var html = highlight(slice, terms);
    if (start > 0) html = '...' + html;
    if (end < parts.length) html += '...';
    return { html: html, hit: true };
  }

  function matchedTagsHtml(tags, terms) {
    var set = termSet(terms);
    var html = [];
    var list = tags || [];
    for (var i = 0; i < list.length; i++) {
      var toks = tokenize(list[i]);
      var hit = false;
      for (var j = 0; j < toks.length; j++) {
        if (set[toks[j]]) hit = true;
      }
      if (hit) html.push('<span class="tag">' + highlight(list[i], terms) + '</span>');
    }
    return html.join(' ');
  }

  function search(skills, query) {
    var list = skills || [];
    var tokens = unique(tokenize(query));
    if (!tokens.length) {
      var plain = [];
      for (var i = 0; i < list.length; i++) {
        plain.push({
          skill: list[i],
          score: 0,
          terms: [],
          nameHtml: '',
          descriptionHtml: '',
          descriptionHit: false,
          matchedTagsHtml: ''
        });
      }
      return plain;
    }
    var index = prepare(list);
    var resolved = [];
    for (var t = 0; t < tokens.length; t++) {
      var alts = resolve(tokens[t], index);
      if (alts.length) resolved.push(alts);
    }
    var hits = [];
    for (var d = 0; d < index.docs.length; d++) {
      var doc = index.docs[d];
      var score = 0;
      var terms = [];
      var matched = false;
      for (var r = 0; r < resolved.length; r++) {
        var best = bestAlt(doc, resolved[r], index.idf);
        if (best.score > 0) {
          matched = true;
          score += best.score;
          terms.push(best.term);
        }
      }
      if (!matched) continue;
      var snip = descriptionSnippet(doc.skill.description, terms);
      hits.push({
        skill: doc.skill,
        score: score,
        terms: terms,
        index: doc.index,
        nameHtml: highlight(doc.skill.name || '', terms),
        descriptionHtml: snip.html,
        descriptionHit: snip.hit,
        matchedTagsHtml: matchedTagsHtml(doc.skill.tags, terms)
      });
    }
    hits.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var an = a.skill.name || '';
      var bn = b.skill.name || '';
      if (an < bn) return -1;
      if (an > bn) return 1;
      return a.index - b.index;
    });
    return hits;
  }

  var api = {
    search: search,
    tokenize: tokenize,
    highlight: highlight,
    oneEdit: oneEdit
  };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HoneypotSearch = api;
})(this);
