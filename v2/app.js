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
    if (data.exploratory !== undefined) validateExploratory(data.exploratory);
    return data;
  }
  function validateExploratory(value) {
    const fail = () => { throw new Error('Invalid provisional exploratory evidence. Regenerate the local bundle.'); };
    if (!value || typeof value !== 'object') fail();
    const schemas = {report: 'exploratory-research-report-v1', cohort: 'provisional-exploratory-cohort-v1', result: 'provisional-exploratory-result-v1'};
    const finite = v => { if (typeof v === 'number' && !Number.isFinite(v)) fail(); if (v && typeof v === 'object') Object.values(v).forEach(finite); };
    for (const [key, schema] of Object.entries(schemas)) {
      const v = value[key]; if (!v || v.schema_version !== schema || v.eligible !== false || v.scientific_approval !== false || v.publication_authorized !== false || v.evaluation_exposure !== 'retrospective_previously_exposed') fail();
      if (key === 'cohort') { if (v.status !== 'PROVISIONAL_NOT_INDEPENDENTLY_VALIDATED') fail(); }
      else if (v.status !== 'EXPLORATORY_ONLY_NOT_VALIDATED' || v.publication_authorized !== false || v.evaluation_exposure !== 'retrospective_previously_exposed') fail();
      finite(v);
    }
    const {report, result, cohort} = value;
    if (typeof report.analysis_id !== 'string' || !report.analysis_id.trim() || report.analysis_id !== result.analysis_id || !/^[0-9a-f]{64}$/.test(report.plan_sha256) || report.plan_sha256 !== result.plan_sha256 || !cohort.counts || !cohort.partitions || JSON.stringify(report.cohort) !== JSON.stringify(cohort)) fail();
    const evaluation = result.evaluation;
    if (!evaluation || evaluation.decision?.classification !== 'NOT_SPECIFIED' || Object.keys(evaluation.models || {}).sort().join() !== Object.keys(modelLabels).sort().join()) fail();
    for (const metrics of Object.values(evaluation.models)) for (const key of ['possession_logloss', 'brier']) if (typeof metrics[key] !== 'number' || !Number.isFinite(metrics[key]) || metrics[key] < 0) fail();
    const paired = evaluation.paired_logloss;
    if (!paired || typeof paired.estimate !== 'number' || !Array.isArray(paired.interval) || paired.interval.length !== 2 || paired.interval.some(v => typeof v !== 'number' || !Number.isFinite(v)) || paired.interval[0] > paired.interval[1] || paired.conditions_on_fitted_models !== true) fail();
    return value;
  }
  function signed(value) { return typeof value === 'number' && Number.isFinite(value) ? `${value >= 0 ? '+' : ''}${number(value, 6)}` : 'Not available'; }
  function exploratorySummary(value) {
    if (!value) return 'No provisional real-data result was included in this export. Synthetic demonstrations above are generated data only.';
    validateExploratory(value);
    return `Analysis ${value.report.analysis_id}. Retrospective previously exposed data; scientific gate blocked.`;
  }
  function renderExploratory(value) {
    const box = target('exploratory-content'); box.append(element('p', exploratorySummary(value)));
    if (!value) return;
    const {report, cohort, result} = value;
    box.append(element('p', `Chosen cohort: ${cohort.cohort?.season || 'Not available'} · ${cohort.cohort?.game_type || 'Not available'}. Included ${number(cohort.counts.included_games)} of ${number(cohort.counts.candidate_games)} candidate games; ${number(cohort.counts.excluded_games)} excluded. Selected ${number(cohort.counts.included_rows)} rows; evaluation ${number(report.split?.test?.rows)} rows / ${number(report.split?.test?.games)} games.`));
    const counts = element('dl', undefined, 'ledger');
    for (const [key, label] of Object.entries({full_frame_games: 'Full frame games', full_frame_rows: 'Full frame rows', candidate_games: 'Candidate games', included_games: 'Included games', excluded_games: 'Excluded games', included_rows: 'Selected rows', out_of_cohort_games: 'Outside chosen cohort'})) appendStat(counts, label, number(cohort.counts[key]));
    const splits = element('dl', undefined, 'ledger');
    for (const name of ['train', 'tune', 'test']) {
      const part = cohort.partitions[name] || {}, selected = report.split?.[name] || {};
      appendStat(splits, `${name[0].toUpperCase()}${name.slice(1)}`, `${number(selected.rows)} rows / ${number(selected.games)} games included; ${number(part.excluded_games)} games excluded`);
    }
    const reasons = element('ul');
    for (const [reason, count] of Object.entries(cohort.exclusion_reason_counts || {})) reasons.append(element('li', `${reason.replaceAll('_', ' ')}: ${number(count)}`));
    if (!reasons.firstChild) reasons.append(element('li', 'No exclusion reason counts supplied.'));
    const details = element('details'); details.append(element('summary', 'Chosen cohort, chronological split and exclusions'), counts, splits, element('h3', 'Exclusion reasons (nonexclusive)'), reasons, element('pre', JSON.stringify({cohort: cohort.cohort, counts: cohort.counts, split: report.split, partitions: cohort.partitions, exclusion_reason_counts_nonexclusive: cohort.exclusion_reason_counts, primary_exclusion_reason_counts: cohort.primary_exclusion_reason_counts}, null, 2)));
    const wrap = element('div', undefined, 'table-wrap'), table = element('table'), head = element('thead'), header = element('tr');
    table.append(element('caption', 'Provisional selected held-out possessions; recorded-call prediction losses'));
    for (const text of ['Algorithm', 'Log loss', 'Brier score', 'Rows / games']) { const th = element('th', text); th.scope = 'col'; header.append(th); } head.append(header); table.append(head);
    const body = element('tbody');
    for (const [key, label] of Object.entries(modelLabels)) { const metrics = result.evaluation.models[key], row = element('tr'), th = element('th', label); th.scope = 'row'; row.append(th); for (const text of [number(metrics.possession_logloss, 6), number(metrics.brier, 6), `${number(metrics.rows)} / ${number(metrics.games)}`]) row.append(element('td', text)); body.append(row); }
    table.append(body); wrap.append(table); box.append(wrap);
    const paired = result.evaluation.paired_logloss;
    box.append(element('p', `History minus identical context log-loss delta: ${signed(paired.estimate)}. Conditional whole-game bootstrap interval (${percent(paired.confidence)}): ${paired.interval.map(signed).join(' to ')}. Negative values favor history on this selected set; no meaningful-gain decision was specified.`, 'annotation'));
    box.append(element('p', `History minus context Brier delta: ${signed(result.evaluation.paired_brier)}.`));
    box.append(element('p', 'The interval conditions on fixed fitted models and development selection. It assumes independent identically distributed games, omits training/selection uncertainty and calendar/series dependence, and has no guaranteed percentile coverage.'));
    const limits = element('ul'); for (const note of report.limitations || []) limits.append(element('li', note)); box.append(limits, details);
    const provenance = element('details'); provenance.append(element('summary', 'Provisional diagnostics, calibration and hash receipts'), element('pre', JSON.stringify({diagnostics: result.diagnostics, evaluation: result.evaluation, provenance: result.provenance, artifacts: report.artifacts}, null, 2))); box.append(provenance);
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
    const status = target('load-status'); status.className = 'status'; status.replaceChildren(element('strong', gate(r)), element('p', `Software: ${String(r.software_status || 'not available').replaceAll('_', ' ').toLowerCase()}. Publication: ${String(r.publication_status || 'not available').replaceAll('_', ' ').toLowerCase()}.`), element('p', 'Development diagnostics are available. Confirmatory evaluation and a new scientific release remain blocked pending independent evidence.'));
    const flow = [['Saved sources', `${number(c.source_files)} input files`], ['Candidate possessions', `${number(c.reconstructed_games)} reconstructed games`], ['Independent audit', r.audit?.status || 'Evidence missing'], ['Validated modeling', `${number(c.eligible_games)} scientific-release eligible games`]];
    flow.forEach(([label, value], i) => { const li = element('li', undefined, i > 1 ? 'blocked' : ''); li.append(element('strong', label), element('span', value)); target('evidence-flow').append(li); });
    const countLabels = {expected_games:'Independent expected games',observed_games:'Observed games',reconstructed_games:'Reconstructed games',quarantined_games:'Quarantined games',possession_rows:'Candidate possession rows',unknown_outcomes:'Unknown possession outcomes',complete_games:'Complete reconstructed games',critical_unresolved_games:'Games with unresolved critical issues',eligible_games:'Scientific-release eligible games',unresolved_transfer_flags:'Unresolved transfer flags',unresolved_violation_flags:'Unresolved violation flags'};
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
    renderExploratory(data.exploratory); list('requirements', r.next_required_evidence); record('audit-record', r.audit); renderFootage(data.footage);
    const provenance = target('provenance-content');
    for (const [label, value] of Object.entries(r.artifacts || {})) { const d = element('details'); d.append(element('summary', label.replaceAll('_', ' ')), element('pre', JSON.stringify(value, null, 2))); provenance.append(d); }
    const inputs = element('details'); inputs.append(element('summary', 'Notebook input byte hashes'), element('pre', JSON.stringify(data.input_files, null, 2))); provenance.append(inputs);
    list('limitations', r.limitations); target('notebook').hidden = false;
  }
  const api = {number, percent, safeUrl, gate, chartPoints, validate, validateExploratory, exploratorySummary, signed};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document !== 'undefined') fetch('data.json').then(response => { if (!response.ok) throw new Error(`Evidence request failed (${response.status}).`); return response.json(); }).then(render).catch(error => { target('notebook').hidden = true; const status = target('load-status'); status.className = 'status error'; status.replaceChildren(element('strong', 'Development evidence could not load'), element('p', `${error.message} Serve the repository over HTTP and check v2/data.json.`)); });
})(typeof globalThis === 'undefined' ? this : globalThis);
