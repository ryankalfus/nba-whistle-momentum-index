/* Development evidence renderer. All external strings enter textContent only. */
(function (root) {
  'use strict';
  const scenarioLabels = {
    independent_constant: 'Independent · constant rate', independent_step: 'Independent · step change',
    independent_smooth: 'Independent · smooth rate change', independent_alternating: 'Independent · alternating rates',
    history_excitation: 'History dependence · excitation', history_inhibition: 'History dependence · inhibition',
    independent_rare: 'Independent · rare events'
  };
  const modelLabels = {base_rate: 'Training base rate', additive_context: 'Additive context', nonlinear_context: 'Nonlinear context', nonlinear_history: 'Same context + past history'};
  function number(value, digits = 0) {
    return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits}) : 'Not available';
  }
  function percent(value) { return typeof value === 'number' && Number.isFinite(value) ? `${number(value * 100, 1)}%` : 'Not available'; }
  function safeUrl(value) {
    if (typeof value !== 'string' || !value || /[\u0000-\u0020\\]/.test(value)) return null;
    if (/^https?:\/\//i.test(value)) { try { return new URL(value).href; } catch { return null; } }
    if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('//') || value.startsWith('/')) return null;
    return value;
  }
  function gate(report) {
    return report.scientific_status === 'PASSED' && report.publication_status === 'AUTHORIZED' ? 'Scientific status requires release review' : 'Scientific gate blocked';
  }
  function chartPoints(probabilities) {
    if (!Array.isArray(probabilities) || probabilities.length < 2 || probabilities.some(p => typeof p !== 'number' || !Number.isFinite(p) || p < 0 || p > 1)) return '';
    return probabilities.map((p, i) => `${(30 + i * 595 / (probabilities.length - 1)).toFixed(2)},${(160 - p * 150).toFixed(2)}`).join(' ');
  }
  function validate(data) {
    if (!data || data.schema_version !== 'research-explorer-v1' || data.report?.schema_version !== 'development-research-report-v1' || !data.report.counts || !data.math?.scenarios || !data.models?.evaluation?.models) throw new Error('The evidence file has an unsupported or incomplete schema. Regenerate the notebook data from the development run.');
    return data;
  }
  function element(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = String(text); if (className) e.className = className; return e; }
  function target(id) { return document.getElementById(id); }
  function appendStat(dl, label, value) { const row = element('div'); row.append(element('dt', label), element('dd', value)); dl.append(row); }
  function record(id, value) { target(id).textContent = JSON.stringify(value ?? {status: 'Not supplied'}, null, 2); }
  function list(id, values) { for (const value of values || []) target(id).append(element('li', typeof value === 'string' ? value : JSON.stringify(value))); }
  function renderScenario(math, key) {
    const s = math.scenarios[key]; if (!s) return;
    target('scenario-title').textContent = scenarioLabels[key] || key;
    const points = chartPoints(s.probabilities); target('probability-line').setAttribute('points', points);
    target('chart-description').textContent = points ? `Baseline foul probabilities for ${s.probabilities.length} generated possessions. ${scenarioLabels[key] || key}.` : 'Probability curve unavailable.';
    target('scenario-note').textContent = s.history_delta === 0 ? 'Each draw is independent. Changes in the baseline rate alone can change the descriptive ratio.' : `After any foul in the previous two possessions, this generator changes the baseline probability by ${number(s.history_delta, 2)}, bounded to [0, 1].`;
    const dl = target('scenario-stats'); dl.replaceChildren();
    appendStat(dl, 'Mean WMI when defined', number(s.conditional_mean_wmi_given_defined, 3));
    appendStat(dl, 'Undefined games', percent(s.undefined_fraction)); appendStat(dl, 'Generated games', number(s.games));
  }
  function renderFootage(footage) {
    const box = target('footage-content');
    if (!footage) { box.append(element('p', 'No footage-access evidence was included in this export. Full-game access and independent review are unverified.')); return; }
    const rows = Array.isArray(footage) ? footage : footage.games || footage.records || footage.routes || [];
    if (Array.isArray(rows)) for (const row of rows) {
      const article = element('article', undefined, 'footage-row');
      article.append(element('h3', row.matchup || row.game_id || row.title || 'Official access route'));
      if (row.date) article.append(element('p', row.date));
      article.append(element('span', row.full_coverage_verified === true ? 'Full coverage evidence supplied; independent review separate' : row.playback_verified === true ? 'Playback verified · full coverage unverified' : 'Playback and full coverage unverified', 'badge'));
      article.append(element('p', row.verification_note || row.note || row.status || row.access_status || 'See the recorded access evidence below.'));
      article.append(element('p', `Access: ${(row.access_status || 'Not supplied').replaceAll('_', ' ')}. Source authorization: ${(row.source_authorization || 'Unverified').replaceAll('_', ' ')}. Duration: ${typeof row.duration_seconds === 'number' ? number(row.duration_seconds / 60, 1) + ' minutes' : 'Not available'}.`));
      const candidates = [row.source_url, row.player_url, row.url, row.official_url, row.game_url, row.replay_url, ...(Array.isArray(row.links) ? row.links.map(v => typeof v === 'string' ? v : v.url) : [])];
      for (const value of [...new Set(candidates)]) { const url = safeUrl(value); if (url) { const a = element('a', value === row.player_url ? 'Open player' : 'Open source route'); a.href = url; a.rel = 'noopener noreferrer'; article.append(a); } }
      box.append(article);
    }
    const details = element('details'); details.append(element('summary', 'Full access record')); const pre = element('pre', JSON.stringify(footage, null, 2)); details.append(pre); box.append(details);
  }
  function render(data) {
    validate(data); const r = data.report, c = r.counts;
    const status = target('load-status'); status.className = 'status'; status.replaceChildren(element('strong', gate(r)), element('p', `Software: ${String(r.software_status || 'not available').replaceAll('_', ' ').toLowerCase()}. Publication: ${String(r.publication_status || 'not available').replaceAll('_', ' ').toLowerCase()}.`), element('p', 'Development diagnostics are available. Empirical evaluation and a new scientific release remain blocked pending independent evidence.'));
    const flow = [['Saved sources', `${number(c.source_files)} input files`], ['Candidate possessions', `${number(c.reconstructed_games)} reconstructed games`], ['Independent audit', r.audit?.status || 'Evidence missing'], ['Empirical models', `${number(c.eligible_games)} eligible games`]];
    flow.forEach(([label, value], i) => { const li = element('li', undefined, i > 1 ? 'blocked' : ''); li.append(element('strong', label), element('span', value)); target('evidence-flow').append(li); });
    const countLabels = {expected_games:'Independent expected games',observed_games:'Observed games',reconstructed_games:'Reconstructed games',quarantined_games:'Quarantined games',possession_rows:'Candidate possession rows',unknown_outcomes:'Unknown possession outcomes',complete_games:'Complete reconstructed games',critical_unresolved_games:'Games with unresolved critical issues',eligible_games:'Eligible for empirical modeling',unresolved_transfer_flags:'Unresolved transfer flags',unresolved_violation_flags:'Unresolved violation flags'};
    for (const [key, label] of Object.entries(countLabels)) appendStat(target('counts'), label, number(c[key]));
    for (const [key, value] of Object.entries(r.versions || {})) target('versions').append(element('p', `${key.replaceAll('_', ' ')}: ${value}`, 'version'));
    const select = target('scenario'); for (const key of Object.keys(data.math.scenarios)) { const option = element('option', scenarioLabels[key] || key); option.value = key; select.append(option); }
    if (data.math.scenarios.independent_step) select.value = 'independent_step';
    select.addEventListener('change', () => renderScenario(data.math, select.value)); renderScenario(data.math, select.value);
    record('math-reference', {seed: data.math.seed, exact_reference: data.math.exact_nonstationary_reference, coverage: data.math.coverage});
    for (const key of Object.keys(modelLabels)) {
      const value = data.models.evaluation.models[key]; if (!value) continue;
      const tr = element('tr'); tr.append(element('th', modelLabels[key] || key)); tr.firstChild.scope = 'row';
      [number(value.possession_logloss, 5), number(value.brier, 5), `${number(value.rows)} / ${number(value.games)}`].forEach(v => tr.append(element('td', v))); target('model-rows').append(tr);
    }
    const paired = data.models.evaluation.paired_logloss || {};
    target('paired-result').append(element('p', `Synthetic history minus context log loss: ${number(paired.estimate, 5)}. Negative favors history.`), element('p', `Synthetic interval: ${Array.isArray(paired.interval) ? paired.interval.map(v => number(v, 5)).join(' to ') : 'Not available'}. This is a generated-data demonstration, not an NBA finding.`));
    record('model-method', {specification: data.models.specification, split: data.models.split, paired_evaluation: paired, decision: data.models.evaluation.decision});
    list('requirements', r.next_required_evidence); record('audit-record', r.audit); renderFootage(data.footage);
    const provenance = target('provenance-content');
    for (const [label, value] of Object.entries(r.artifacts || {})) { const d = element('details'); d.append(element('summary', label.replaceAll('_', ' ')), element('pre', JSON.stringify(value, null, 2))); provenance.append(d); }
    const inputs = element('details'); inputs.append(element('summary', 'Notebook input byte hashes'), element('pre', JSON.stringify(data.input_files, null, 2))); provenance.append(inputs);
    list('limitations', r.limitations); target('notebook').hidden = false;
  }
  const api = {number, percent, safeUrl, gate, chartPoints, validate};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document !== 'undefined') fetch('data.json').then(response => { if (!response.ok) throw new Error(`Evidence request failed (${response.status}).`); return response.json(); }).then(render).catch(error => { target('notebook').hidden = true; const status = target('load-status'); status.className = 'status error'; status.replaceChildren(element('strong', 'Development evidence could not load'), element('p', `${error.message} Serve the repository over HTTP and check v2/data.json.`)); });
})(typeof globalThis === 'undefined' ? this : globalThis);
