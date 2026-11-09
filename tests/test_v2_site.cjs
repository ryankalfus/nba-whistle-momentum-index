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

function exploratoryFixture() {
  const flags = {eligible: false, scientific_approval: false, publication_authorized: false, evaluation_exposure: 'retrospective_previously_exposed'};
  const cohort = {schema_version: 'provisional-exploratory-cohort-v1', ...flags, status: 'PROVISIONAL_NOT_INDEPENDENTLY_VALIDATED', counts: {}, partitions: {}};
  const report = {schema_version: 'exploratory-research-report-v1', ...flags, status: 'EXPLORATORY_ONLY_NOT_VALIDATED', analysis_id: '<img src=x onerror=alert(1)>', plan_sha256: 'a'.repeat(64), cohort, limitations: ['No independent validation']};
  const result = {schema_version: 'provisional-exploratory-result-v1', ...flags, status: report.status, analysis_id: report.analysis_id, plan_sha256: report.plan_sha256, evaluation: {models: Object.fromEntries(['base_rate', 'additive_context', 'nonlinear_context', 'nonlinear_history'].map(name => [name, {possession_logloss: .5, brier: .2}])), paired_logloss: {estimate: -.001, interval: [-.002, .001], conditions_on_fitted_models: true}, decision: {classification: 'NOT_SPECIFIED'}}};
  return {report, cohort, result};
}

test('provisional results preserve blocked gate and signed paired differences', () => {
  const evidence = exploratoryFixture();
  assert.equal(ui.validateExploratory(evidence), evidence);
  assert.match(ui.exploratorySummary(evidence), /scientific gate blocked/);
  assert.equal(ui.gate(evidence.report), 'Scientific gate blocked');
  assert.equal(ui.signed(-.001), '-0.001000');
  assert.equal(ui.signed(.001), '+0.001000');
  assert.equal(ui.signed(null), 'Not available');
});

test('provisional schema, flags, identities, metrics and decision fail closed', () => {
  const mutations = [
    e => { e.report.schema_version = 'unknown'; },
    e => { e.cohort.status = 'PASSED'; },
    e => { e.result.analysis_id = 'other'; },
    e => { e.result.plan_sha256 = 'b'.repeat(64); },
    e => { e.report.plan_sha256 = 'invalid'; e.result.plan_sha256 = 'invalid'; },
    e => { e.result.evaluation.models.base_rate.brier = Infinity; },
    e => { e.result.evaluation.models.base_rate.possession_logloss = null; },
    e => { e.result.evaluation.paired_logloss.interval = [0, NaN]; },
    e => { e.result.evaluation.paired_logloss.conditions_on_fitted_models = false; },
    e => { e.result.evaluation.decision.classification = 'USEFUL'; },
    e => { delete e.result.evaluation.models.nonlinear_history; },
  ];
  for (const role of ['report', 'cohort', 'result']) for (const flag of ['eligible', 'scientific_approval', 'publication_authorized']) mutations.push(e => { e[role][flag] = true; });
  for (const mutate of mutations) { const e = exploratoryFixture(); mutate(e); assert.throws(() => ui.validateExploratory(e), /Invalid provisional/); }
});

test('no result has an honest generated-data-only empty state', () => {
  assert.match(ui.exploratorySummary(), /No provisional real-data result was included/);
  assert.match(ui.exploratorySummary(), /Synthetic demonstrations above are generated data only/);
});

async function renderedEvidence(exploratory, counts = {}) {
  const nodes = new Map();
  function node(tagName) {
    return {tagName, children: [], textContent: '', append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = items; }, setAttribute() {}, addEventListener() {}, get firstChild() { return this.children[0]; }, set innerHTML(value) { throw new Error(`Unsafe HTML insertion: ${value}`); }};
  }
  const document = {createElement: node, getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); }};
  const data = {schema_version: 'research-explorer-v1', report: {schema_version: 'development-research-report-v1', counts}, math: {scenarios: {}}, models: {evaluation: {models: {}}}};
  if (exploratory !== undefined) data.exploratory = exploratory;
  require('node:vm').runInNewContext(require('node:fs').readFileSync(require.resolve('../v2/app.js'), 'utf8'), {document, fetch: async () => ({ok: true, json: async () => data})});
  await new Promise(resolve => setImmediate(resolve));
  const text = n => [n.textContent, ...n.children.map(text)].join(' ');
  return {nodes, text};
}

test('rendered provisional section uses text only and leaves unavailable counts missing', async () => {
  const evidence = exploratoryFixture();
  const {nodes, text} = await renderedEvidence(evidence);
  const content = text(nodes.get('exploratory-content'));
  assert.match(content, /<img src=x onerror=alert\(1\)>/);
  assert.match(content, /Not available/);
  assert.match(content, /Conditional whole-game bootstrap interval/);
  assert.match(content, /no meaningful-gain decision was specified/);
  assert.match(text(nodes.get('load-status')), /Scientific gate blocked/);
  assert.equal(nodes.get('notebook').hidden, false);
});

test('rendered empty state and malformed evidence do not display real-data losses', async () => {
  const empty = await renderedEvidence();
  assert.match(empty.text(empty.nodes.get('exploratory-content')), /No provisional real-data result was included/);
  assert.doesNotMatch(empty.text(empty.nodes.get('exploratory-content')), /0\.500000/);
  const evidence = exploratoryFixture(); evidence.result.scientific_approval = true;
  const invalid = await renderedEvidence(evidence);
  assert.equal(invalid.nodes.get('notebook').hidden, true);
  assert.match(invalid.text(invalid.nodes.get('load-status')), /could not load/);
  assert.equal(invalid.nodes.has('exploratory-content'), false);
});


test('provisional model table precedes the complete detailed cohort accounting', async () => {
  const evidence = exploratoryFixture();
  evidence.cohort.cohort = {season: 'fixture-season', game_type: 'fixture-type'};
  evidence.cohort.counts = {full_frame_games: 101, full_frame_rows: 102, candidate_games: 103, included_games: 104, excluded_games: 105, included_rows: 106, out_of_cohort_games: 107, full_frame_unknown_outcomes: 108};
  evidence.report.split = {train: {rows: 201, games: 202}, tune: {rows: 203, games: 204}, test: {rows: 205, games: 206}};
  evidence.cohort.partitions = {train: {excluded_games: 301}, tune: {excluded_games: 302}, test: {excluded_games: 303}};
  evidence.cohort.exclusion_reason_counts = Object.fromEntries(Array.from({length: 10}, (_, i) => [`fixture_reason_${i}`, i + 401]));
  const {nodes, text} = await renderedEvidence(evidence);
  const box = nodes.get('exploratory-content');
  const tableIndex = box.children.findIndex(n => n.className === 'table-wrap');
  const detailsIndex = box.children.findIndex(n => n.tagName === 'details' && text(n).includes('Chosen cohort, chronological split and exclusions'));
  assert.ok(tableIndex >= 0 && detailsIndex > tableIndex);
  const beforeTable = box.children.slice(0, tableIndex).map(text).join(' ');
  assert.match(beforeTable, /fixture-season · fixture-type/);
  assert.match(beforeTable, /Included 104 of 103 candidate games; 105 excluded/);
  assert.match(beforeTable, /Selected 106 rows; evaluation 205 rows \/ 206 games/);
  assert.doesNotMatch(beforeTable, /Full frame games|fixture reason/);
  const details = text(box.children[detailsIndex]);
  for (const key of Object.keys(evidence.cohort.counts)) assert.ok(details.includes(`"${key}"`));
  for (const [reason, count] of Object.entries(evidence.cohort.exclusion_reason_counts)) assert.ok(details.includes(`${reason.replaceAll('_', ' ')}: ${count}`));
  for (const partition of Object.values(evidence.report.split)) assert.ok(details.includes(`${partition.rows} rows / ${partition.games} games included`));
  assert.equal(box.children[detailsIndex].open, undefined);
});

test('zero eligibility is labeled scientific release for old and provisional payloads', async () => {
  for (const evidence of [undefined, exploratoryFixture()]) {
    const rendered = await renderedEvidence(evidence, {eligible_games: 0});
    assert.match(rendered.text(rendered.nodes.get('evidence-flow')), /Validated modeling 0 scientific-release eligible games/);
    assert.match(rendered.text(rendered.nodes.get('counts')), /Scientific-release eligible games 0/);
    assert.match(rendered.text(rendered.nodes.get('load-status')), /Scientific gate blocked/);
  }
});
