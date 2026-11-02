const test = require('node:test');
const assert = require('node:assert/strict');
const ui = require('../v2/app.js');

test('missing scientific values remain missing rather than becoming zero', () => {
  for (const value of [null, undefined, NaN, Infinity, '0', '']) {
    assert.equal(ui.number(value), 'Not available');
    assert.equal(ui.percent(value), 'Not available');
  }
  assert.equal(ui.number(0), '0');
  assert.equal(ui.number(1193032), '1,193,032');
  assert.equal(ui.percent(0.67275), '67.3%');
});
test('scientific gate fails closed on missing or partial authorization', () => {
  for (const report of [{}, {scientific_status: 'BLOCKED'}, {scientific_status: 'PASSED'}, {publication_status: 'AUTHORIZED'}]) assert.equal(ui.gate(report), 'Scientific gate blocked');
  assert.equal(ui.gate({scientific_status: 'PASSED', publication_status: 'AUTHORIZED'}), 'Scientific status requires release review');
});
test('data links reject script schemes, protocol-relative links and control characters', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,x', '//evil.test', '/private', 'https://a.test/\nx', '\\evil', 'file:///private', null]) assert.equal(ui.safeUrl(value), null);
  assert.equal(ui.safeUrl('https://www.nba.com/game/123'), 'https://www.nba.com/game/123');
  assert.equal(ui.safeUrl('../docs/RESEARCH_PROTOCOL.md'), '../docs/RESEARCH_PROTOCOL.md');
});
test('probability chart uses actual values and rejects unknown or impossible probabilities', () => {
  assert.equal(ui.chartPoints([0, 1]), '30.00,160.00 625.00,10.00');
  for (const points of [[], [0.2], [null, 1], [-0.1, 0.4], [0, 1.1]]) assert.equal(ui.chartPoints(points), '');
});
test('schema rejection prevents plausible-looking fallback metrics', () => {
  for (const value of [null, {}, {schema_version: 'research-explorer-v1', report: {counts:{}}}]) assert.throws(() => ui.validate(value), /unsupported or incomplete/);
  const data = {schema_version: 'research-explorer-v1', report: {schema_version:'development-research-report-v1',counts:{}},math:{scenarios:{}},models:{evaluation:{models:{}}}};
  assert.equal(ui.validate(data), data);
});
