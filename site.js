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
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value, digits = 3) {
  const parsed = numberValue(value);
  return parsed === null ? "N/A" : parsed.toFixed(digits);
}

function formatPercentile(value) {
  const parsed = numberValue(value);
  return parsed === null ? "N/A" : `${parsed.toFixed(1)}th`;
}

function compactDate(value) {
  if (!value) {
    return "Unknown date";
  }
  return value.slice(0, 10);
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
    game.game_date_et,
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
  if (value > 1.05) {
    return "More whistle momentum after recent defensive fouls.";
  }
  if (value < 0.95) {
    return "Less whistle momentum after recent defensive fouls.";
  }
  return "Close to neutral short-term whistle momentum.";
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
  els.selected.innerHTML = `
    <p class="eyebrow">${game.season} | ${game.season_type}</p>
    <h3>${game.matchup || game.game_id}</h3>
    <p class="game-date">${gameLabel(game)}</p>
    <div class="selected-stats">
      <div>
        <span>WMI</span>
        <strong>${formatNumber(game.WMI, 4)}</strong>
      </div>
      <div>
        <span>Percentile</span>
        <strong>${formatPercentile(game.wmi_percentile)}</strong>
      </div>
      <div>
        <span>Possessions</span>
        <strong>${game.possessions || "N/A"}</strong>
      </div>
    </div>
    <p>${interpretation(game.WMI)}</p>
  `;
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
    state.games = parseCsv(text).map((game) => ({
      ...game,
      searchText: searchableText(game),
    }));
    state.filtered = state.games;
    populateFilters();
    applyFilters();
    selectGame(state.games[0]);
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
}
