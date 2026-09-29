"""Offline WMI audit and expanding-season prediction. See the saved protocol."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from wmi_possessions import PARSER_VERSION, components, reconstruct, sequence_features
from wmi_utils import add_recent_foul_columns, calculate_wmi

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "research/validation_2026_09_12"
CACHE = ROOT / "research/hypotheses_2026_09_12/cache"
SITE = ROOT / "site-data"
SEED = 20260912
CATEGORICAL = ["offense_team", "defense_team", "period_bucket"]
NUMERIC = [
    "score_difference_before",
    "score_margin_before",
    "seconds_left_before",
    "home_defense",
    "defense_team_fouls_before",
    "defense_bonus_before",
    "late_strategy_context",
]
HISTORY = [
    f"{prefix}_{k}"
    for k in range(1, 6)
    for prefix in ["foul_lag", "same_defense_foul_lag"]
]
USECOLS = [
    "gameId",
    "actionNumber",
    "orderNumber",
    "clock",
    "timeActual",
    "period",
    "teamId",
    "teamTricode",
    "possession",
    "scoreHome",
    "scoreAway",
    "actionType",
    "subType",
    "descriptor",
    "description",
    "personId",
    "foulDrawnPersonId",
    "shotResult",
    "isFieldGoal",
    "area",
]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def legacy_summary(actions):
    valid = actions[
        actions.possession.isin(actions.teamId.dropna().unique())
    ].sort_values(["orderNumber", "actionNumber"])
    groups = valid.possession.ne(valid.possession.shift()).cumsum()
    foul = (
        valid.actionType.eq("foul")
        & ~valid.subType.fillna("")
        .str.lower()
        .isin(["offensive", "technical", "double technical"])
        & valid.teamId.ne(valid.possession)
    )
    table = add_recent_foul_columns(
        pd.DataFrame(
            {
                "foul_called_this_possession": foul.groupby(groups)
                .max()
                .astype(int)
                .values
            }
        )
    )
    return len(table), calculate_wmi(table)["WMI"]


def build(max_games=None):
    manifest = json.loads((CACHE.parent / "source_manifest.json").read_text())
    source_map = {entry["file"]: entry for entry in manifest}
    summary_rows, audit, failures, manual = [], [], [], []
    partitions = []
    for label in ["2020", "2021", "2022", "2023", "2024", "po_2024"]:
        name = f"cdnnba_{label}.tar.xz"
        path = CACHE / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source_map[name]["sha256"]:
            raise ValueError(f"Input checksum mismatch: {name}")
        with tarfile.open(path) as archive:
            raw = pd.read_csv(
                archive.extractfile(f"cdnnba_{label}.csv"),
                usecols=lambda c: c in USECOLS,
                low_memory=False,
            )
        year = int(label[-4:])
        season = f"{year}-{str(year + 1)[-2:]}"
        game_type = "Playoffs" if label.startswith("po") else "Regular Season"
        tables = []
        for i, (gid, actions) in enumerate(raw.groupby("gameId", sort=True)):
            if max_games and i >= max_games:
                break
            gid = str(int(gid)).zfill(10)
            try:
                table = sequence_features(
                    add_recent_foul_columns(reconstruct(actions, gid))
                )
                table["season"] = season
                table["season_type"] = game_type
                table["game_date"] = str(
                    pd.to_datetime(actions.timeActual, utc=True, format="mixed")
                    .min()
                    .tz_convert("America/New_York")
                    .date()
                )
                table["period_bucket"] = table.period.map(
                    lambda x: str(x) if x <= 4 else "OT"
                )
                result = calculate_wmi(table)
                old_count, old_wmi = legacy_summary(actions)
                detail = components(table)
                delta = (
                    result["WMI"] - old_wmi
                    if old_wmi is not None and result["WMI"] is not None
                    else None
                )
                audit.append(
                    dict(
                        game_id=gid,
                        season=season,
                        season_type=game_type,
                        old_possessions=old_count,
                        new_possessions=len(table),
                        old_wmi_same_source=old_wmi,
                        new_wmi=result["WMI"],
                        wmi_change=delta,
                        unassigned_foul_events=int(
                            table.unassigned_foul_events.iloc[0]
                        ),
                        invalid_timed_events=int(table.invalid_timed_events.iloc[0]),
                        administrative_groups_removed=int(
                            table.administrative_groups_removed.iloc[0]
                        ),
                    )
                )
                row = dict(
                    game_id=gid,
                    season=season,
                    season_type=game_type,
                    game_date_et=table.game_date.iloc[0],
                    home_team=table.home_team.iloc[0],
                    away_team=table.away_team.iloc[0],
                    possessions=len(table),
                    **result,
                    **detail,
                    parser_version=PARSER_VERSION,
                    source=name,
                    reliability="Descriptive; interval not validated",
                )
                row["matchup"] = f"{row['away_team']} @ {row['home_team']}"
                foul_rows = table[table.F_t.eq(1)]
                marks = foul_rows.defense_team.tolist()
                row["same_team_transitions"] = sum(
                    a == b for a, b in zip(marks, marks[1:])
                )
                row["opposite_team_transitions"] = sum(
                    a != b for a, b in zip(marks, marks[1:])
                )
                summary_rows.append(row)
                timeline = []
                for t in table.itertuples():
                    for event in json.loads(t.foul_events):
                        timeline.append({"possession": t.possession_number, **event})
                dump(
                    SITE / "timelines" / f"{gid}.json",
                    {"game_id": gid, "possessions": len(table), "events": timeline},
                )
                # Deterministic audit excerpts, including boundaries, FT and offensive fouls.
                if i < 2:
                    selected = actions[
                        (actions.actionType.isin(["foul", "freethrow", "rebound"]))
                        | (
                            actions.clock.isin(
                                ["PT12M00.00S", "PT00M00.00S", "PT05M00.00S"]
                            )
                        )
                    ]
                    for a in selected.head(80).to_dict("records"):
                        manual.append({"game_id": gid, "season": season, **a})
                tables.append(table)
            except Exception as exc:
                failures.append({"game_id": gid, "source": name, "error": str(exc)})
                print("failed", gid, str(exc), flush=True)
            if (i + 1) % 200 == 0:
                print(label, i + 1, "games", flush=True)
        table = pd.concat(tables, ignore_index=True)
        target = OUT / f"possessions_{label}.csv.gz"
        table.to_csv(target, index=False, compression={"method": "gzip", "mtime": 0})
        partitions.append(
            {
                "file": target.name,
                "rows": len(table),
                "games": table.game_id.nunique(),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
        print("saved", target.name, len(table), flush=True)
        del raw, table, tables
    games = pd.DataFrame(summary_rows)
    regular = games[games.season_type.eq("Regular Season")]
    reference = regular.WMI.dropna().sort_values().to_numpy()
    # Midrank empirical percentile, relative to a fixed recalculated regular-season cohort.
    games["wmi_percentile"] = [
        (
            np.searchsorted(reference, v, "left")
            + np.searchsorted(reference, v, "right")
            + 1
        )
        / 2
        / len(reference)
        * 100
        if np.isfinite(v)
        else np.nan
        for v in games.WMI
    ]
    games["wmi_percentile"] = games.wmi_percentile.clip(upper=100)
    games.to_csv(SITE / "audited_games.csv", index=False)
    pd.DataFrame(audit).to_csv(OUT / "parser_comparison.csv", index=False)
    pd.DataFrame(manual).to_csv(OUT / "audit_event_excerpts.csv", index=False)
    pd.DataFrame(failures, columns=["game_id", "source", "error"]).to_csv(
        OUT / "failures.csv", index=False
    )
    dump(
        OUT / "dataset_manifest.json",
        {
            "parser_version": PARSER_VERSION,
            "sources": [
                source_map[f"cdnnba_{x}.tar.xz"]
                for x in ["2020", "2021", "2022", "2023", "2024", "po_2024"]
            ],
            "partitions": partitions,
        },
    )
    dump(
        SITE / "summary.json",
        {
            "audited_games": len(games),
            "comparison_games": len(reference),
            "mean_wmi": float(reference.mean()),
            "median_wmi": float(np.median(reference)),
            "parser_version": PARSER_VERSION,
            "failures": len(failures),
        },
    )


def model(history=False):
    cols = NUMERIC + (HISTORY if history else [])
    transform = ColumnTransformer(
        [
            ("numeric", StandardScaler(), cols),
            ("category", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return make_pipeline(
        transform,
        LogisticRegression(C=1.0, max_iter=500, solver="lbfgs", random_state=SEED),
    )


def scores(y, p):
    return dict(
        log_loss=float(log_loss(y, p)),
        brier=float(brier_score_loss(y, p)),
        roc_auc=float(roc_auc_score(y, p)),
        average_precision=float(average_precision_score(y, p)),
    )


def paired_interval(frame, reps=1000):
    eps = 1e-12
    y = frame.F_t.to_numpy()
    losses = []
    for col in ["context", "history"]:
        p = np.clip(frame[col].to_numpy(), eps, 1 - eps)
        losses.append(-(y * np.log(p) + (1 - y) * np.log(1 - p)))
    d = pd.DataFrame(
        {"game_id": frame.game_id.to_numpy(), "delta": losses[1] - losses[0]}
    )
    groups = d.groupby("game_id").delta.agg(["sum", "count", "mean"])
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(reps):
        idx = rng.integers(0, len(groups), len(groups))
        sample = groups.iloc[idx]
        draws.append(sample["sum"].sum() / sample["count"].sum())
    return {
        "delta_log_loss": float(d.delta.mean()),
        "ci_low": float(np.percentile(draws, 2.5)),
        "ci_high": float(np.percentile(draws, 97.5)),
        "equal_game_delta": float(groups["mean"].mean()),
    }


def evaluate():
    regular = []
    for year in range(2020, 2025):
        d = pd.read_csv(
            OUT / f"possessions_{year}.csv.gz",
            dtype={"game_id": str, "period_bucket": str},
        )
        regular.append(
            d[
                CATEGORICAL
                + NUMERIC
                + HISTORY
                + ["F_t", "game_id", "season", "possession_number"]
            ]
        )
    all_data = pd.concat(regular, ignore_index=True)
    results = []
    calibration = []
    residuals = []
    predictions = []
    for year in [2022, 2023, 2024]:
        season = f"{year}-{str(year + 1)[-2:]}"
        train = all_data[all_data.season < season]
        test = all_data[all_data.season == season].copy()
        context = model()
        history = model(True)
        print("fitting", season, "train", len(train), "test", len(test), flush=True)
        context.fit(train, train.F_t)
        history.fit(train, train.F_t)
        if max(context[-1].n_iter_) >= 500 or max(history[-1].n_iter_) >= 500:
            raise RuntimeError("Model failed to converge")
        test["context"] = context.predict_proba(test)[:, 1]
        test["history"] = history.predict_proba(test)[:, 1]
        tests = [("Regular Season", test)]
        if year == 2024:
            playoff = pd.read_csv(
                OUT / "possessions_po_2024.csv.gz",
                dtype={"game_id": str, "period_bucket": str},
            )
            playoff["context"] = context.predict_proba(playoff)[:, 1]
            playoff["history"] = history.predict_proba(playoff)[:, 1]
            tests.append(("Playoffs", playoff))
        for game_type, sample in tests:
            for scope, subset in [
                ("All possessions", sample),
                ("Late strategy excluded", sample[sample.late_strategy_context.eq(0)]),
            ]:
                row = dict(
                    season=season,
                    game_type=game_type,
                    scope=scope,
                    train_games=int(train.game_id.nunique()),
                    test_games=int(subset.game_id.nunique()),
                    possessions=len(subset),
                    **paired_interval(subset),
                )
                for label in ["context", "history"]:
                    row.update(
                        {
                            f"{label}_{k}": v
                            for k, v in scores(subset.F_t, subset[label]).items()
                        }
                    )
                results.append(row)
            for label in ["context", "history"]:
                # Calibration is descriptive on held-out predictions, not a refit of predictions.
                x = logit(np.clip(sample[label].to_numpy(), 1e-8, 1 - 1e-8)).reshape(
                    -1, 1
                )
                cal = LogisticRegression(C=1e8, solver="lbfgs", max_iter=200).fit(
                    x, sample.F_t
                )
                bins = pd.qcut(sample[label], 10, duplicates="drop")
                for bucket, group in sample.groupby(bins, observed=True):
                    calibration.append(
                        dict(
                            season=season,
                            game_type=game_type,
                            model=label,
                            bin=str(bucket),
                            n=len(group),
                            predicted=float(group[label].mean()),
                            observed=float(group.F_t.mean()),
                            intercept=float(cal.intercept_[0]),
                            slope=float(cal.coef_[0, 0]),
                        )
                    )
            p = sample[
                ["game_id", "possession_number", "F_t", "context", "history"]
            ].copy()
            p["season"] = season
            p["game_type"] = game_type
            predictions.append(p)
            for gid, g in sample.groupby("game_id"):
                residuals.append(
                    dict(
                        game_id=gid,
                        season=season,
                        game_type=game_type,
                        observed=int(g.F_t.sum()),
                        expected=float(g.context.sum()),
                        residual=float((g.F_t - g.context).sum()),
                    )
                )
    result = pd.DataFrame(results)
    result.to_csv(OUT / "prediction_results.csv", index=False)
    pd.DataFrame(calibration).to_csv(OUT / "calibration.csv", index=False)
    pd.DataFrame(residuals).to_csv(OUT / "heldout_residuals.csv", index=False)
    pd.concat(predictions).to_csv(
        OUT / "heldout_predictions.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    final = result[
        (result.season.isin(["2023-24", "2024-25"]))
        & result.game_type.eq("Regular Season")
        & result.scope.eq("All possessions")
    ]
    passed = bool(
        (final.ci_high < 0).all() and (final.history_brier <= final.context_brier).all()
    )
    dump(
        OUT / "expansion_decision.json",
        {
            "passed": passed,
            "rule": "Both final regular-season evaluations have paired log-loss CI below zero and no worse Brier.",
            "decision": "Proceed to directional forecasting"
            if passed
            else "Defer directional forecasting; history has not met the replication gate.",
        },
    )
    print(result.to_string(index=False), flush=True)
    report(result, passed)


def report(results, passed):
    audit = pd.read_csv(OUT / "parser_comparison.csv", dtype={"game_id": str})
    stored = pd.read_csv(
        ROOT / "wmi_games_2020_21_to_2025_26.csv", dtype={"game_id": str}
    )
    stored.game_id = stored.game_id.str.zfill(10)
    joined = audit[
        audit.season.eq("2024-25") & audit.season_type.eq("Regular Season")
    ].merge(stored[["game_id", "WMI"]], on="game_id")
    joined["source_difference"] = joined.old_wmi_same_source - joined.WMI
    joined.to_csv(OUT / "source_comparison_2024_25.csv", index=False)
    manifest = json.loads((OUT / "dataset_manifest.json").read_text())
    headers = [
        "Season / cohort",
        "Games",
        "Context log loss",
        "History log loss",
        "Change (95% game-bootstrap CI)",
        "Brier change",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in results[results.scope.eq("All possessions")].itertuples():
        lines.append(
            f"| {r.season} {r.game_type} | {r.test_games} | {r.context_log_loss:.6f} | {r.history_log_loss:.6f} | {r.delta_log_loss:+.6f} ({r.ci_low:+.6f}, {r.ci_high:+.6f}) | {r.history_brier - r.context_brier:+.6f} |"
        )
    text = f"""# WMI validation and replication

This report supersedes the prediction claims in the August exploratory report. WMI's formula is unchanged. Parser version: `{PARSER_VERSION}`. Seed: {SEED}. This is retrospective validation using final corrected play-by-play, not a prospective live-data trial.

## Dataset and parser audit

Processed {sum(p["games"] for p in manifest["partitions"]):,} games and {sum(p["rows"] for p in manifest["partitions"]):,} possessions from commit-pinned archives. The source manifest records checksums; compressed possession partitions preserve all model inputs, outcomes, foul/player IDs and event descriptions. Reconstruction uses source possession ownership on live-event rows plus explicit period boundaries; substitutions, reviews and period markers cannot create possessions. Technical-only ownership segments are removed; returning segments are joined only when no terminal live play occurred.

- {int((audit.new_possessions != audit.old_possessions).sum()):,} games change possession count versus the old parser on the SAME CDN source.
- Mean absolute game WMI change from the period/admin correction: {audit.wmi_change.abs().mean():.6f}; maximum: {audit.wmi_change.abs().max():.6f}.
- On {len(joined):,} overlapping 2024–25 regular-season games, mean absolute CDN-versus-stored-mobile WMI difference using the old grouping is {joined.source_difference.abs().mean():.6f}. This separates feed differences from the parser correction.
- Unassigned foul events across games: {int(audit.unassigned_foul_events.sum()):,}. These are retained as audit counts, not silently assigned to a team possession.
- Invalid timed events: {int(audit.invalid_timed_events.sum()):,}. See failures.csv for game-level failures.

The start clock and score are taken from the preceding recorded event, resetting at period boundaries. This is a reconstructed reference point and can precede actual live-ball control. Regulation and overtime durations are handled separately; future overtime never enters predictors. Team-foul/bonus reconstruction includes regulation/OT thresholds and the last-two-minute rule, and excludes offensive, technical and double fouls from the team count. Rare rule exceptions and retrospective source edits remain limitations.

## Matched prediction comparison

Both models use exactly the same games and basketball-context variables. The history model adds five global foul lags and five same-defending-team foul lags. Training expands only through earlier seasons, with fixed logistic regression settings and no hyperparameter search. All possessions are included in the primary analysis. A separate sensitivity excludes all pre-specified late-strategy contexts, regardless of whether a foul happened.

{chr(10).join(lines)}

Negative change favors adding history. Confidence intervals resample entire games (1,000 draws). Full metrics, equal-game loss changes and late-strategy sensitivity are in prediction_results.csv. Calibration bins and intercept/slope are in calibration.csv; these describe held-out predictions and do not recalibrate test predictions. Historical 2024–25 exploratory results were already known, so the final season is a retrospective holdout rather than an untouched prospective test.

## Expansion decision

{"The replication gate passed. A directional forecasting follow-up is warranted." if passed else "The replication gate did not pass. Directional forecasting, survival/Hawkes models, Transformers and substitution-policy models are deferred. The current results do not establish a reliable incremental forecasting benefit across the final two seasons."}

The gate requires the upper paired loss interval to be below zero in both final regular-season evaluations, with no worse Brier score. It is a resource-allocation criterion, not proof of an officiating mechanism.

## Public interpretation and uncertainty

The site retains original snapshot rows for games without recalculated data, labels parser versions, and uses separate explicitly named percentile cohorts. Recalculated games expose the exact WMI decomposition, group sizes, both means and a team-labeled foul timeline. Same-team/opposite-team transitions are descriptive counts. No random-mark baseline is interpreted as evidence of makeup calls.

Per-game confidence intervals are withheld because the tested circular block method does not provide consistent coverage across the simulation scenarios; see the interval coverage study. Counts and denominator warnings are descriptive support diagnostics, not a validated reliability classifier. A percentile does not establish statistical significance, and a confidence interval containing one would not establish equivalence.

## Limits and next evidence

The dataset stores current-possession shot/rim attempts and free throws as outcomes, never as pre-possession predictors. It does not identify drives, paint touches, validated lineups, all player foul-trouble states or the official responsible for each call. Bonus status is reconstructed from feed labels; rare exceptions need additional adjudication. Observed-minus-expected foul volume is a context-model residual, not adjusted WMI or evidence of call error. Published final feeds may differ from what a live observer originally saw.

The original equation uses global windows across period boundaries and truncated windows at game edges. Those choices are preserved. Source ownership can still disagree with live-ball control in unusual administrative/retained-ball sequences; automated invariants and event-level spot checks do not replace comprehensive film review.

## Reproduce

Run `python validate_wmi.py` after the pinned inputs have been acquired by the existing fetch script. Use `--evaluate-only` to refit from saved partitions. `--max-games` is a development option and must use a separate output directory via `--output`; it must not overwrite full-release artifacts.

Sources: [NBA foul/penalty rules](https://official.nba.com/rule-no-12-fouls-and-penalties/), [NBA timing rules](https://official.nba.com/rule-no-5-scoring-and-timing/), [leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). Raw archive URLs and hashes are in dataset_manifest.json.
"""
    (OUT / "report.md").write_text(text)


def main():
    global OUT, SITE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--max-games", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_games and not args.output:
        parser.error("--max-games requires --output to protect the full release")
    if args.output:
        OUT = args.output
        SITE = OUT / "site-data"
    OUT.mkdir(parents=True, exist_ok=True)
    SITE.mkdir(parents=True, exist_ok=True)
    if not args.evaluate_only:
        build(args.max_games)
    if not args.build_only:
        evaluate()


if __name__ == "__main__":
    main()
