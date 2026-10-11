// Ranked search: 10 queries and the skill that should come first.
// Run from the repo root: node tests/test_search.js
var assert = require('assert');
var fs = require('fs');
var path = require('path');
var search = require('../search.js');

var skills = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../api/skills.json'), 'utf8')
).skills;

var QUERIES = [
  ['Kalshi', 'kalshi'],
  ['kalsh', 'kalshi'],
  ['odds', 'the-odds-api'],
  ['pdf text', 'pdf-text'],
  ['crontab', 'cron'],
  ['playwright', 'playwright-mcp'],
  ['imagmagick', 'image-optimize'],
  ['webhook', 'webhooks'],
  ['python sdk', 'oids-python-sdk'],
  ['browser', 'playwright-mcp']
];

var failed = 0;

assert.strictEqual(QUERIES.length, 10);

QUERIES.forEach(function (row) {
  var q = row[0];
  var expected = row[1];
  var hits = search.search(skills, q);
  var top = hits[0] && hits[0].skill.name;
  if (top !== expected) {
    failed++;
    console.error(
      'FAIL', JSON.stringify(q), 'expected', expected, 'got', top,
      hits.slice(0, 3).map(function (h) {
        return h.skill.name + ' (' + h.score.toFixed(3) + ')';
      }).join(', ')
    );
  }
});

var kalsh = search.search(skills, 'kalsh')[0];
assert.ok(kalsh.nameHtml.indexOf('<mark>kalshi</mark>') !== -1);
assert.ok(kalsh.descriptionHtml.indexOf('<mark>Kalshi</mark>') !== -1);
assert.ok(kalsh.score > 0);

var odds = search.search(skills, 'odds');
assert.strictEqual(odds[0].skill.name, 'the-odds-api');
assert.ok(odds[0].descriptionHit);
assert.ok(odds[0].descriptionHtml.indexOf('<mark>odds</mark>') !== -1);
assert.ok(!odds.some(function (h) { return h.skill.name === 'oids'; }));

var cron = search.search(skills, 'cron')[0];
assert.strictEqual(cron.skill.name, 'cron');
assert.strictEqual(cron.descriptionHit, false);
assert.ok(cron.matchedTagsHtml.indexOf('<mark>cron</mark>') !== -1);

var imag = search.search(skills, 'imagmagick')[0];
assert.ok(imag.descriptionHtml.indexOf('<mark>ImageMagick</mark>') !== -1);

var empty = search.search(skills, '   ');
assert.strictEqual(empty.length, skills.length);
assert.strictEqual(empty[0].skill.name, skills[0].name);
assert.strictEqual(empty[0].score, 0);

var none = search.search(skills, 'zzzzzzzz');
assert.strictEqual(none.length, 0);

var nasty = search.search(
  [{
    name: '<script>',
    description: 'prefix <img src=x onerror=alert(1)> odds suffix',
    tags: ['<b>odds</b>']
  }],
  'odds'
)[0];
assert.ok(nasty.descriptionHtml.indexOf('<img') === -1);
assert.ok(nasty.descriptionHtml.indexOf('&lt;img') !== -1);
assert.ok(nasty.descriptionHtml.indexOf('<mark>odds</mark>') !== -1);
assert.ok(nasty.nameHtml.indexOf('<script>') === -1);
assert.ok(nasty.matchedTagsHtml.indexOf('<b>') === -1);
assert.ok(nasty.matchedTagsHtml.indexOf('&lt;b&gt;') !== -1);

var longDesc = 'aaaa '.repeat(40) + 'odds ' + 'bbbb '.repeat(40);
var windowed = search.search(
  [{ name: 'long', description: longDesc, tags: [] }],
  'odds'
)[0];
assert.ok(windowed.descriptionHtml.length < longDesc.length);
assert.ok(windowed.descriptionHtml.indexOf('...') === 0);
assert.ok(windowed.descriptionHtml.indexOf('<mark>odds</mark>') !== -1);
assert.ok(windowed.descriptionHtml.slice(-3) === '...');

assert.strictEqual(search.oneEdit('kalsh', 'kalshi'), true);
assert.strictEqual(search.oneEdit('odds', 'oids'), true);
assert.strictEqual(search.oneEdit('pdf', 'pdftext'), false);
assert.strictEqual(search.oneEdit('cron', 'cron'), false);

if (failed) {
  console.error(failed + ' query failure(s)');
  process.exit(1);
}
console.log('ok ' + QUERIES.length + ' queries');
