const DATA_URL = "wmi_search_games_2019_2026.csv";
const RESULT_BATCH_SIZE = 60;

const state = {
  games: [],
  filtered: [],
  selected: null,
  visibleCount: RESULT_BATCH_SIZE,
};

const els = {
  form: document.querySelector("#wmi-search-form"),
  input: document.querySelector("#wmi-search-input"),
  season: document.querySelector("#wmi-season-filter"),
  type: document.querySelector("#wmi-type-filter"),
  meta: document.querySelector("#wmi-search-meta"),
  list: document.querySelector("#wmi-result-list"),
  selected: document.querySelector("#wmi-selected-game"),
};

const TEAM_ALIASES = {
  ATL: ["atlanta", "hawks", "atlanta hawks"],
  BOS: ["boston", "celtics", "boston celtics"],
  BKN: ["brooklyn", "nets", "brooklyn nets", "new jersey nets"],
  CHA: ["charlotte", "hornets", "charlotte hornets", "bobcats", "charlotte bobcats"],
  CHI: ["chicago", "bulls", "chicago bulls"],
  CLE: ["cleveland", "cavaliers", "cavs", "cleveland cavaliers"],
  DAL: ["dallas", "mavericks", "mavs", "dallas mavericks"],
  DEN: ["denver", "nuggets", "denver nuggets"],
  DET: ["detroit", "pistons", "detroit pistons"],
  GSW: ["golden state", "warriors", "golden state warriors"],
  HOU: ["houston", "rockets", "houston rockets"],
  IND: ["indiana", "pacers", "indiana pacers"],
  LAC: ["la clippers", "los angeles clippers", "clippers"],
  LAL: ["la lakers", "los angeles lakers", "lakers"],
  MEM: ["memphis", "grizzlies", "memphis grizzlies"],
  MIA: ["miami", "heat", "miami heat"],
  MIL: ["milwaukee", "bucks", "milwaukee bucks"],
  MIN: ["minnesota", "timberwolves", "wolves", "minnesota timberwolves"],
  NOP: ["new orleans", "pelicans", "pels", "new orleans pelicans"],
  NYK: ["new york", "knicks", "new york knicks", "ny knicks"],
  OKC: ["oklahoma city", "thunder", "okc thunder", "oklahoma city thunder"],
  ORL: ["orlando", "magic", "orlando magic"],
  PHI: ["philadelphia", "sixers", "76ers", "philadelphia 76ers", "philadelphia sixers"],
  PHX: ["phoenix", "suns", "phoenix suns"],
  POR: ["portland", "trail blazers", "blazers", "portland trail blazers"],
  SAC: ["sacramento", "kings", "sacramento kings"],
  SAS: ["san antonio", "spurs", "san antonio spurs"],
  TOR: ["toronto", "raptors", "toronto raptors"],
  UTA: ["utah", "jazz", "utah jazz"],
  WAS: ["washington", "wizards", "washington wizards", "bullets", "washington bullets"],
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      value += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(value);
      value = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") {
        i += 1;
      }
      row.push(value);
      if (row.some((cell) => cell !== "")) {
        rows.push(row);
      }
      row = [];
      value = "";
    } else {
      value += char;
    }
  }

  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }

  const headers = rows.shift() || [];
  return rows.map((cells) =>
    Object.fromEntries(headers.map((header, index) => [header, cells[index] || ""])),
  );
}

function numberValue(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value, digits = 3) {
  const parsed = numberValue(value);
  return parsed === null ? "N/A" : parsed.toFixed(digits);
}

function formatPercentile(value) {
  const parsed = numberValue(value);
  return parsed === null ? "N/A" : `${parsed.toFixed(1)}%`;
}

function compactDate(value) {
  if (!value) {
    return "Unknown date";
  }
  return /^\d{8}$/.test(value) ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}` : value.slice(0, 10);
}

function gameLabel(game) {
  const score =
    game.away_score && game.home_score ? `, ${game.away_score}-${game.home_score}` : "";
  return `${compactDate(game.game_date_et)} | ${game.matchup || game.game_id}${score}`;
}

function teamAliases(code) {
  return TEAM_ALIASES[code] || [];
}

function searchableText(game) {
  return [
    game.season,
    game.season_type,
    game.game_id,
    compactDate(game.game_date_et),
    game.away_team,
    game.home_team,
    game.matchup,
    ...teamAliases(game.away_team),
    ...teamAliases(game.home_team),
  ]
    .join(" ")
    .toLowerCase();
}

function interpretation(wmi) {
  const value = numberValue(wmi);
  if (value === null) {
    return "This game did not have enough valid possession groups to compute WMI.";
  }
  if (value > 1) return "The observed WMI ratio is above 1. This is a descriptive difference, not evidence of statistical significance or referee intent.";
  if (value < 1) return "The observed WMI ratio is below 1. This is a descriptive difference, not evidence of statistical significance or referee intent.";
  return "The two observed group means are equal. This alone does not establish statistical equivalence.";
}

function populateFilters() {
  const seasons = [...new Set(state.games.map((game) => game.season).filter(Boolean))].sort();
  for (const season of seasons) {
    const option = document.createElement("option");
    option.value = season;
    option.textContent = season;
    els.season.appendChild(option);
  }
}

function applyFilters() {
  const terms = els.input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const season = els.season.value;
  const type = els.type.value;

  state.filtered = state.games.filter((game) => {
    if (season && game.season !== season) {
      return false;
    }
    if (type && game.season_type !== type) {
      return false;
    }
    if (terms.length && !terms.every((term) => game.searchText.includes(term))) {
      return false;
    }
    return true;
  });
  state.visibleCount = RESULT_BATCH_SIZE;

  if (!state.filtered.length) {
    state.selected = null;
    renderEmptySelection();
  } else if (!state.selected || !state.filtered.some((game) => game.game_id === state.selected.game_id)) {
    state.selected = state.filtered[0];
    renderSelectedGame(state.selected);
  }

  renderResults();
}

function renderResults() {
  const total = state.filtered.length;
  els.list.replaceChildren();

  if (!total) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No games match that search.";
    els.list.appendChild(empty);
    updateMeta();
    return;
  }

  appendResultBatch(0, Math.min(state.visibleCount, total));
  updateMeta();
}

function appendResultBatch(start, end) {
  const existingMore = els.list.querySelector(".load-more-state");
  if (existingMore) {
    existingMore.remove();
  }

  const shown = state.filtered.slice(start, end);
  for (const game of shown) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "game-result";
    if (state.selected && state.selected.game_id === game.game_id) {
      button.classList.add("is-selected");
    }
    button.innerHTML = `
      <span>
        <strong>${game.matchup || game.game_id}</strong>
        <small>${compactDate(game.game_date_et)} | ${game.season} | ${game.season_type}</small>
      </span>
      <span class="result-wmi">${formatNumber(game.WMI)}</span>
    `;
    button.addEventListener("click", () => selectGame(game));
    els.list.appendChild(button);
  }

  if (end < state.filtered.length) {
    const more = document.createElement("p");
    more.className = "load-more-state";
    more.textContent = "Scroll for more games";
    els.list.appendChild(more);
  }
}

function updateMeta() {
  const total = state.filtered.length;
  const shown = Math.min(state.visibleCount, total);
  els.meta.textContent = `${total.toLocaleString()} matching games. Showing ${shown.toLocaleString()}.`;
}

function selectGame(game) {
  state.selected = game;
  renderSelectedGame(game);
  renderResults();
}

function renderSelectedGame(game) {
  const audited = game.parser_version === "period_start_v2";
  const reference = audited
    ? "Recalculated regular-season games, 2020–21 through 2024–25 (period-boundary parser v2)."
    : "Original search snapshot: regular season, playoffs and play-in, 2019–20 through the March 2026 snapshot (original parser).";
  const stat = (label, value) => `<div><span>${label}</span><strong>${value}</strong></div>`;
  const denominator = numberValue(game.mean_M_t_where_L_t_eq_0);
  const support = Math.min(numberValue(game.n1_count_L_t_eq_1) ?? Infinity, numberValue(game.n0_count_L_t_eq_0) ?? Infinity);
  els.selected.innerHTML = `
    <p class="eyebrow">${game.season} | ${game.season_type}</p>
    <h3>${game.matchup || game.game_id}</h3>
    <p class="game-date">${gameLabel(game)}</p>
    <p class="version-label">${audited ? "Recalculated · parser v2" : "Original snapshot · awaiting recalculation"}</p>
    <div class="selected-stats">
      ${stat("WMI", formatNumber(game.WMI))}
      ${stat("Percentile", formatPercentile(game.wmi_percentile))}
      ${stat("Possessions", game.possessions || "N/A")}
    </div>
    <p class="reference-note"><strong>Percentile reference:</strong> ${reference}</p>
    <p>${interpretation(game.WMI)}</p>
    <details open><summary>Why this game received this score</summary>
      <div class="diagnostic-grid">
        ${stat("Recent-foul possessions (n1)", game.n1_count_L_t_eq_1 || "N/A")}
        ${stat("Other possessions (n0)", game.n0_count_L_t_eq_0 || "N/A")}
        ${stat("Numerator · mean M after recent fouls", formatNumber(game.mean_M_t_where_L_t_eq_1))}
        ${stat("Denominator · mean M without recent fouls", formatNumber(game.mean_M_t_where_L_t_eq_0))}
        ${stat("Immediate foul ratio", formatNumber(game.immediate_ratio))}
        ${stat("Continuation ratio", formatNumber(game.continuation_ratio))}
      </div>
      <p class="muted-text">WMI divides the numerator by the denominator. Where defined, immediate ratio × continuation ratio gives the same WMI.</p>
      ${audited ? `<p>Consecutive foul possessions: <strong>${game.same_team_transitions}</strong> same-team transitions; <strong>${game.opposite_team_transitions}</strong> opposite-team transitions. These counts do not identify makeup calls.</p>` : "<p>Components and timelines require reprocessing the source events. They are unavailable for this original snapshot row.</p>"}
    </details>
    <p class="support-note">${denominator === 0 ? "WMI is undefined because its denominator is zero. " : ""}${support !== null && support < 30 ? "Fewer than 30 possessions in at least one comparison group; interpret the ratio cautiously. This is a sample-size notice, not a validated reliability threshold. " : ""}Per-game confidence intervals are not displayed: the tested bootstrap method did not achieve consistent coverage across simulated scenarios.</p>
    ${audited ? '<details><summary>Foul timeline · team and subtype</summary><div id="foul-timeline" aria-live="polite">Loading foul events…</div></details>' : ""}
  `;
  if (audited) loadTimeline(game.game_id);
}

async function loadTimeline(gameId) {
  try {
    const response = await fetch(`site-data/timelines/${gameId}.json`);
    if (!response.ok) throw new Error("Timeline unavailable");
    const data = await response.json();
    if (state.selected?.game_id !== gameId) return;
    const container = document.querySelector("#foul-timeline");
    if (!container) return;
    container.replaceChildren();
    const list = document.createElement("ol");
    list.className = "foul-timeline";
    for (const event of data.events) {
      const item = document.createElement("li");
      const seconds = event.clock % 60;
      const clock = `${Math.floor(event.clock / 60)}:${(Number.isInteger(seconds) ? String(seconds).padStart(2, "0") : seconds.toFixed(1).padStart(4, "0"))}`;
      item.textContent = `Possession ${event.possession} · Q${event.period} ${clock} · ${event.team} · ${event.descriptor || event.subtype}: ${event.description}`;
      list.appendChild(item);
    }
    container.appendChild(list);
    if (!data.events.length) container.textContent = "No counted defensive fouls.";
  } catch {
    if (state.selected?.game_id === gameId) {
      const container = document.querySelector("#foul-timeline");
      if (container) container.textContent = "Foul timeline could not be loaded. The game summary remains available.";
    }
  }
}

function renderEmptySelection() {
  els.selected.innerHTML = `
    <p class="eyebrow">No game selected</p>
    <h3>No matching games</h3>
    <p class="muted-text">Try another team, date, season, or game ID.</p>
  `;
}

async function loadSearchData() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`Could not load ${DATA_URL}`);
    }
    const text = await response.text();
    let merged = parseCsv(text).map(game => ({...game, game_id: game.game_id.padStart(10, "0")}));
    try {
      const auditedResponse = await fetch("site-data/audited_games.csv");
      if (!auditedResponse.ok) throw new Error("Recalculated data unavailable");
      const audited = parseCsv(await auditedResponse.text());
      const gamesById = new Map(merged.map(game => [game.game_id, game]));
      audited.forEach(game => gamesById.set(game.game_id, {...gamesById.get(game.game_id), ...game}));
      merged = [...gamesById.values()];
    } catch {
      document.querySelector("#validation-status").textContent = "Recalculated data could not be loaded. Search is showing the original snapshot.";
    }
    merged.sort((a,b) => compactDate(b.game_date_et).localeCompare(compactDate(a.game_date_et)) || b.game_id.localeCompare(a.game_id));
    state.games = merged.map((game) => ({
      ...game,
      searchText: searchableText(game),
    }));
    state.filtered = state.games;
    populateFilters();
    applyFilters();
    if (state.games.length) selectGame(state.games[0]);
  } catch (error) {
    els.meta.textContent = "WMI search data could not be loaded.";
    els.list.replaceChildren();
    els.selected.innerHTML = `
      <p class="eyebrow">Search unavailable</p>
      <h3>Data file did not load</h3>
      <p class="muted-text">${error.message}</p>
    `;
  }
}

if (els.form) {
  els.form.addEventListener("input", applyFilters);
  els.form.addEventListener("submit", (event) => event.preventDefault());
  els.list.addEventListener("scroll", () => {
    const nearBottom = els.list.scrollTop + els.list.clientHeight >= els.list.scrollHeight - 80;
    if (nearBottom && state.visibleCount < state.filtered.length) {
      const previousCount = state.visibleCount;
      state.visibleCount += RESULT_BATCH_SIZE;
      const nextCount = Math.min(state.visibleCount, state.filtered.length);
      appendResultBatch(previousCount, nextCount);
      updateMeta();
    }
  });
  loadSearchData();
  loadValidation();
}

async function loadValidation() {
  try {
    const response = await fetch("research/validation_2026_09_12/prediction_results.csv");
    if (!response.ok) return;
    const rows = parseCsv(await response.text()).filter(row => row.scope === "All possessions");
    const result = document.querySelector("#validation-result");
    const final = rows.find(row => row.season === "2024-25" && row.game_type === "Regular Season");
    if (final) result.textContent = `Recent foul history added a small amount of predictive information. In ${final.season} regular-season testing, log loss changed by ${formatNumber(final.delta_log_loss,6)}. This supports further research, not a strong forecasting claim.`;
    const table = document.createElement("table");
    table.className = "validation-table";
    const caption = document.createElement("caption");
    caption.textContent = "Matched model comparison · lower log loss is better";
    table.appendChild(caption);
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    for (const label of ["Test season", "Context", "+ Foul history", "Change · 95% interval"]) {
      const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = label; header.appendChild(cell);
    }
    head.appendChild(header); table.appendChild(head);
    const body = document.createElement("tbody");
    for (const row of rows) {
      const tr = document.createElement("tr");
      for (const value of [`${row.season} ${row.game_type}`, formatNumber(row.context_log_loss,6), formatNumber(row.history_log_loss,6), `${formatNumber(row.delta_log_loss,6)} (${formatNumber(row.ci_low,6)}, ${formatNumber(row.ci_high,6)})`]) {
        const cell = document.createElement("td"); cell.textContent = value; tr.appendChild(cell);
      }
      body.appendChild(tr);
    }
    table.appendChild(body);
    const wrapper = document.createElement("div"); wrapper.className = "table-scroll"; wrapper.appendChild(table);
    result.after(wrapper);
  } catch { /* The report link remains available if the optional summary fails. */ }
}
