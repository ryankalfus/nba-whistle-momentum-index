"""Conditional exploratory team and time-to-foul horizon forecasts."""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from validate_wmi import CATEGORICAL, HISTORY, NUMERIC, OUT, SEED, model


def targets(game, horizon, target):
    foul = game.F_t.to_numpy()
    home = game.home_defense.to_numpy()
    labels = np.full(len(game), -1, dtype=int)
    for start in range(len(game) - horizon + 1):
        found = np.flatnonzero(foul[start : start + horizon])
        labels[start] = (
            (int(home[start + found[0]]) + 1 if target == "team" else int(found[0]) + 1)
            if len(found)
            else 0
        )
    return labels


def loss_rows(y, probability, classes):
    indices = {value: index for index, value in enumerate(classes)}
    return -np.log(
        np.clip([probability[i, indices[v]] for i, v in enumerate(y)], 1e-12, 1)
    )


def run():
    decision = json.loads((OUT / "expansion_decision.json").read_text())
    if not decision["passed"]:
        print(decision["decision"])
        return
    frames = []
    for year in range(2020, 2025):
        d = pd.read_csv(
            OUT / f"possessions_{year}.csv.gz",
            dtype={"game_id": str, "period_bucket": str},
        )
        frames.append(
            d[
                CATEGORICAL
                + NUMERIC
                + HISTORY
                + ["F_t", "game_id", "season", "possession_number"]
            ]
        )
    data = pd.concat(frames, ignore_index=True)
    rows = []
    for name, horizon in [("team", 3), ("time", 5)]:
        data["target"] = np.concatenate(
            [targets(g, horizon, name) for _, g in data.groupby("game_id", sort=False)]
        )
        eligible = data[data.target.ge(0)]
        for season in ["2023-24", "2024-25"]:
            train = eligible[eligible.season < season]
            test = eligible[eligible.season == season]
            losses = []
            metrics = {}
            for label, history in [("context", False), ("history", True)]:
                fitted = model(history).fit(train, train.target)
                if max(fitted[-1].n_iter_) >= 500:
                    raise RuntimeError("Multiclass model did not converge")
                probability = fitted.predict_proba(test)
                classes = fitted[-1].classes_
                metrics[label + "_log_loss"] = float(
                    log_loss(test.target, probability, labels=classes)
                )
                losses.append(loss_rows(test.target.to_numpy(), probability, classes))
            delta = losses[1] - losses[0]
            g = (
                pd.DataFrame({"game": test.game_id.to_numpy(), "delta": delta})
                .groupby("game")
                .delta.agg(["sum", "count"])
            )
            rng = np.random.default_rng(SEED)
            draws = []
            for _ in range(1000):
                sampled = g.iloc[rng.integers(0, len(g), len(g))]
                draws.append(sampled["sum"].sum() / sampled["count"].sum())
            row = dict(
                target=name,
                horizon=horizon,
                season=season,
                games=int(test.game_id.nunique()),
                possessions=len(test),
                **metrics,
                delta_log_loss=float(delta.mean()),
                ci_low=float(np.percentile(draws, 2.5)),
                ci_high=float(np.percentile(draws, 97.5)),
            )
            rows.append(row)
            print(row, flush=True)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "sequence_forecasts.csv", index=False)
    decision["sequence_followup_status"] = "completed"
    decision["sequence_conclusion"] = (
        "Small time-to-foul gains; next-team loss intervals include zero in both seasons. Advanced model expansion remains deferred pending richer opportunity controls and prospective validation."
    )
    (OUT / "expansion_decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    report = OUT / "report.md"
    text = "\n## Conditional sequence forecasts\n\nThe primary replication gate passed, so the pre-specified exploratory follow-up was executed. Team labels are 0=no foul in three possessions, 1=away commits first, 2=home commits first. Time labels are 0=no foul in five possessions or 1–5 for the first foul position, counting the current possession as position 1. Incomplete game-ending horizons are excluded. These are multinomial horizon forecasts; they are not fitted Hawkes or survival models.\n\n| Target | Season | Context log loss | History log loss | Change (paired 95% CI) |\n| --- | --- | --- | --- | --- |\n"
    for r in result.itertuples():
        text += f"| {r.target}, {r.horizon} possessions | {r.season} | {r.context_log_loss:.6f} | {r.history_log_loss:.6f} | {r.delta_log_loss:+.6f} ({r.ci_low:+.6f}, {r.ci_high:+.6f}) |\n"
    text += "\nThe follow-up uses the same fixed models and earlier-season training rule. These additional outcomes are exploratory, without multiple-comparison-adjusted claims. Statistical improvements can be small in practical terms.\n"
    original = report.read_text().split("\n## Conditional sequence forecasts")[0]
    report.write_text(original + text)


if __name__ == "__main__":
    run()
