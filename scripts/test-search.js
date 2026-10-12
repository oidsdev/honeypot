#!/usr/bin/env node
/* 10 queries against api/skills.json. Each must rank the expected skill first
   and highlight the expected token. Run: node scripts/test-search.js */
var fs = require('fs');
var path = require('path');
var search = require('../search.js');

var skills = JSON.parse(fs.readFileSync(path.join(__dirname, '../api/skills.json'), 'utf8')).skills;

var QUERIES = [
  { q: 'sqlite', top: 'sqlite', mark: 'sqlite' },
  { q: 'sportsbook', top: 'the-odds-api', mark: 'sportsbook' },
  { q: 'pdf', top: 'pdf-text', mark: 'pdf' },
  { q: 'heartbeat', top: 'honeypot', mark: 'heartbeat' },
  { q: 'python', top: 'oids-python-sdk', mark: 'python' },
  { q: 'compression', top: 'image-optimize', mark: 'compression' },
  { q: 'sqite', top: 'sqlite', mark: 'sqlite' },
  { q: 'webhoks', top: 'webhooks', mark: 'webhooks' },
  { q: 'imagemagik', top: 'image-optimize', mark: 'imagemagick' },
  { q: 'workspace skill', top: 'skill-creator', mark: 'workspace' }
];

function marked(text, ranges) {
  var out = [];
  for (var i = 0; i < ranges.length; i++) out.push(text.slice(ranges[i][0], ranges[i][1]).toLowerCase());
  return out;
}

function highlights(hit) {
  var s = hit.skill;
  var found = marked(s.name || '', hit.ranges.name).concat(marked(s.description || '', hit.ranges.description));
  var tags = s.tags || [];
  for (var i = 0; i < tags.length; i++) found = found.concat(marked(tags[i], (hit.ranges.tags || [])[i] || []));
  return found;
}

var failed = 0;

QUERIES.forEach(function (c) {
  var hits = search.rank(skills, c.q);
  var top = hits[0];
  var name = top && top.skill.name;
  var marks = top ? highlights(top) : [];
  var problems = [];
  if (name !== c.top) problems.push('top ' + name + ' !== ' + c.top);
  if (hits.length > 1 && !(hits[0].score > hits[1].score)) problems.push('tie with ' + hits[1].skill.name);
  if (marks.indexOf(c.mark) === -1) problems.push('highlights [' + marks.join(', ') + '] missing ' + c.mark);
  if (!top.snippet || !top.snippet.ranges.length) problems.push('empty snippet');
  else {
    var snipMarks = marked(top.snippet.text, top.snippet.ranges);
    if (snipMarks.indexOf(c.mark) === -1) problems.push('snippet missing ' + c.mark);
  }
  if (problems.length) {
    failed++;
    console.error('FAIL ' + JSON.stringify(c.q) + ' — ' + problems.join('; '));
    hits.slice(0, 3).forEach(function (h) {
      console.error('  ' + h.score.toFixed(3) + ' ' + h.skill.name);
    });
  } else {
    console.log('ok  ' + JSON.stringify(c.q) + ' -> ' + name);
  }
});

var all = search.rank(skills, '');
if (all.length !== skills.length) {
  failed++;
  console.error('FAIL empty query returned ' + all.length);
} else {
  for (var i = 0; i < skills.length; i++) {
    if (all[i].skill.name !== skills[i].name || all[i].score !== 0) {
      failed++;
      console.error('FAIL empty query reordered at ' + i);
      break;
    }
  }
  if (!failed) console.log('ok  empty query keeps index order');
}

if (failed) {
  console.error(failed + ' failed');
  process.exit(1);
}
console.log(QUERIES.length + ' queries passed');
