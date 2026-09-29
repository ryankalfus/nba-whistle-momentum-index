"""Reproducible, separately stored follow-up study of hypotheses H1-H18.

Raw public archives are cached with SHA256 provenance. No production WMI files
are overwritten. Run with --fetch-only to download inputs, then without that
flag to build audited research tables and the report.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
from collections import defaultdict
import tarfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import numpy as np
import requests
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrix
from scipy.special import expit
from scipy.stats import spearmanr, norm
from statsmodels.stats.multitest import multipletests
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    log_loss,
    brier_score_loss,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "research" / "hypotheses_2026_09_12"
CACHE = OUT / "cache"
SEED = 20260912
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

TITLES = {
    1: "Short-term dependence after context adjustment",
    2: "Immediate persistence versus future continuation",
    3: "Decay over possession distance",
    4: "Same-team versus opposite-team foul direction",
    5: "Close games versus blowouts",
    6: "Bonus status as a modifier of momentum",
    7: "Playoffs versus regular season",
    8: "Home-court effects on foul direction",
    9: "Crowd presence and foul sequencing",
    10: "Defender foul trouble and opponent strategy",
    11: "Whether coaches bench foul-troubled players too conservatively",
    12: "Player behavior after drawing a foul",
    13: "The 2022 transition-take-foul rule",
    14: "Whistle patterns after successful challenges",
    15: "Stability of referee-crew sequencing profiles",
    16: "Foul sequences and subsequent scoring",
    17: "Live foul features and win prediction",
    18: "WMI versus foul volume and consequences (additional hypothesis)",
}
BASE = "score_diff + margin + time_scaled + C(period_bucket) + C(offense) + C(defense) + home_offense"
RICH = BASE + " + bonus + prior_rim_attempts + prior_three_attempts + prior_fta"


class Study:
    def __init__(self):
        self.results = []
        self.details = defaultdict(list)
        self.failures = []
        self.rng = np.random.default_rng(SEED)

    def record(
        self,
        h,
        test,
        estimate,
        low=np.nan,
        high=np.nan,
        p=np.nan,
        n=0,
        games=0,
        unit="",
        **kwargs,
    ):
        self.results.append(
            dict(
                hypothesis=f"H{h}",
                test=test,
                estimate=float(estimate),
                ci_low=float(low),
                ci_high=float(high),
                p_value=float(p),
                n=int(n),
                games=int(games),
                unit=unit,
                **kwargs,
            )
        )

    def model(self, h, label, data, formula, terms, binary=True):
        if len(data) < 50 or data.game_id.nunique() < 20:
            raise ValueError(f"Insufficient observations for {label}: {len(data)} rows")
        if binary:
            model = smf.glm(
                formula, data=data, family=sm.families.Binomial(), missing="raise"
            )
            fitted = model.fit(
                cov_type="cluster", cov_kwds={"groups": data.game_id}, maxiter=75
            )
            if not fitted.converged:
                raise ValueError(f"Nonconverged fit: {label}")
        else:
            fitted = smf.ols(formula, data=data, missing="raise").fit(
                cov_type="cluster", cov_kwds={"groups": data.game_id}
            )
        ci = fitted.conf_int()
        for term in terms:
            b = float(fitted.params[term])
            lo, hi = ci.loc[term]
            self.record(
                h,
                label + ": " + term,
                math.exp(b) if binary else b,
                math.exp(lo) if binary else lo,
                math.exp(hi) if binary else hi,
                fitted.pvalues[term],
                len(data),
                data.game_id.nunique(),
                "odds ratio" if binary else "coefficient",
            )
        self.details[h].append(
            {
                "model": label,
                "formula": formula,
                "rows": len(data),
                "games": int(data.game_id.nunique()),
                "converged": True,
            }
        )
        coef = pd.DataFrame(
            {
                "term": fitted.params.index,
                "coefficient": fitted.params.values,
                "se": fitted.bse.values,
                "p": fitted.pvalues.values,
            }
        )
        coef.to_csv(
            OUT / (f"H{h}_" + re.sub(r"\W+", "_", label) + "_coefficients.csv"),
            index=False,
        )
        return fitted

    def paired(self, h, label, data, value, unit="difference"):
        data = data.dropna(subset=[value]).copy()
        agg = data.groupby("game_id")[value].agg(["sum", "count"])
        if len(agg) < 10:
            raise ValueError(f"Only {len(agg)} games for {label}")
        observed = agg["sum"].sum() / agg["count"].sum()
        ix = self.rng.integers(0, len(agg), size=(1000, len(agg)))
        draws = agg["sum"].to_numpy()[ix].sum(axis=1) / agg["count"].to_numpy()[ix].sum(
            axis=1
        )
        lo, hi = np.quantile(draws, [0.025, 0.975])
        se = np.std(draws, ddof=1)
        p = 2 * norm.sf(abs(observed / se)) if se > 0 else np.nan
        self.record(h, label, observed, lo, hi, p, len(data), len(agg), unit)


def component_stats(df, window=2):
    rows = []
    for game_id, g in df.groupby("game_id", sort=False):
        row = {"game_id": game_id}
        for level in (0, 1):
            mask = g[f"L{window}"].eq(level)
            row[f"n{level}"] = int(mask.sum())
            row[f"f{level}"] = int(g.loc[mask, "F_t"].sum())
            row[f"c{level}"] = int(
                (g.loc[mask, "F_t"] * g.loc[mask, f"N{window}"]).sum()
            )
        rows.append(row)
    out = pd.DataFrame(rows)
    out["immediate"] = (out.f1 / out.n1) / (out.f0 / out.n0)
    out["continuation"] = (1 + out.c1 / out.f1) / (1 + out.c0 / out.f0)
    out["WMI"] = ((out.f1 + out.c1) / out.n1) / ((out.f0 + out.c0) / out.n0)
    return out


def add_research_outcomes(df):
    frames = []
    for _, g in df.groupby("game_id", sort=False):
        g = g.copy()
        g["last_foul_defense"] = g.defense.where(g.F_t.eq(1)).ffill().shift(1)
        g["since_foul"] = g.pos - g.pos.where(g.F_t.eq(1)).ffill().shift(1)
        g["same_defense_as_last_foul"] = g.defense.eq(g.last_foul_defense).astype(int)
        # Full future windows only. The last five rows are censored, not zero.
        net = (g.home_points - g.away_points).to_numpy()
        for name, values in {
            "future_net5": net,
            "future_fta5": g.fta.to_numpy(),
            "future_turnovers5": g.turnovers.to_numpy(),
            "future_rim5": g.rim_attempts.to_numpy(),
        }.items():
            g[name] = [
                np.sum(values[i + 1 : i + 6]) if i + 5 < len(g) else np.nan
                for i in range(len(g))
            ]
        g["future_net5"] *= 2 * g.home_offense - 1
        g["future_clock_seconds5"] = g.end_elapsed.shift(-5) - g.end_elapsed
        frames.append(g)
    out = pd.concat(frames, ignore_index=True)
    out["time_scaled"] = out.reg_remaining / 720
    out["close"] = out.margin.le(5).astype(int)
    out["blowout"] = out.margin.ge(15).astype(int)
    return out


def main_hypotheses(study, df, games):
    primary = df[df.year.eq(2024) & df.postseason.eq(0)].copy()
    primary.to_parquet(CACHE / "primary_analysis.parquet", index=False)
    fit = study.model(1, "context_adjusted", primary, "F_t ~ L2 + " + RICH, ["L2"])
    eta = fit.model.exog @ fit.params.to_numpy()
    beta = fit.params["L2"]
    low_eta = eta - beta * primary.L2.to_numpy()
    study.record(
        1,
        "standardized probability change",
        np.mean(expit(low_eta + beta) - expit(low_eta)),
        n=len(primary),
        games=primary.game_id.nunique(),
        unit="probability points",
    )
    nonlate = primary[primary.late_strategy.eq(0)].copy()
    study.model(
        1,
        "exclude_all_late_strategy_possessions",
        nonlate,
        "F_t ~ L2 + " + RICH,
        ["L2"],
    )
    # After game demeaning, offense and defense team dummies are negatives of
    # one another. Keep one set to avoid a rank-deficient covariance matrix.
    design = dmatrix(
        "L2 + " + RICH.replace(" + C(defense)", ""), primary, return_type="dataframe"
    )
    within = design - design.groupby(primary.game_id).transform("mean")
    within = within.loc[:, within.std().gt(1e-10)]
    response = primary.F_t - primary.groupby("game_id").F_t.transform("mean")
    fixed = sm.OLS(response, within).fit(
        cov_type="cluster", cov_kwds={"groups": primary.game_id}
    )
    lo, hi = fixed.conf_int().loc["L2"]
    study.record(
        1,
        "within-game fixed-effect linear probability sensitivity",
        fixed.params["L2"],
        lo,
        hi,
        fixed.pvalues["L2"],
        len(primary),
        primary.game_id.nunique(),
        "probability difference",
    )
    study.details[1].append(
        {
            "within_game_control": "Demeaned linear probability model removes fixed game and assigned-crew levels; not a mixed-effects logistic or lineup-adjusted fit."
        }
    )

    for window in (1, 2, 3, 5, 10):
        stats = component_stats(primary, window)
        stats.to_csv(OUT / f"game_components_window_{window}.csv", index=False)
        a = stats[["n0", "n1", "f0", "f1", "c0", "c1"]].to_numpy()
        ix = study.rng.integers(0, len(a), size=(1000, len(a)))
        draw = a[ix].sum(axis=1)

        def calc(v):
            immediate = (v[..., 3] / v[..., 1]) / (v[..., 2] / v[..., 0])
            continuation = (1 + v[..., 5] / v[..., 3]) / (1 + v[..., 4] / v[..., 2])
            return [immediate, continuation, immediate * continuation]

        estimates = calc(a.sum(axis=0))
        distributions = calc(draw)
        for label, point, values in zip(
            ("immediate", "continuation", "WMI"), estimates, distributions
        ):
            lo, hi = np.quantile(values, [0.025, 0.975])
            study.record(
                2 if window == 2 else 3,
                f"window {window}: {label}",
                point,
                lo,
                hi,
                n=len(primary),
                games=len(a),
                unit="ratio",
            )
        if window == 2:
            finite = stats.replace([np.inf, -np.inf], np.nan).dropna(
                subset=["immediate", "continuation", "WMI"]
            )
            study.details[2].append(
                {
                    "factorization_max_error": float(
                        (finite.WMI - finite.immediate * finite.continuation)
                        .abs()
                        .max()
                    ),
                    "valid_game_decompositions": len(finite),
                }
            )
    study.model(
        3,
        "distance_specific",
        primary,
        "F_t ~ lag1 + lag2 + lag3 + lag4 + lag5 + " + RICH,
        [f"lag{i}" for i in range(1, 6)],
    )

    directional = primary[primary.since_foul.between(1, 10)].copy()
    study.model(
        4,
        "opportunity_conditioned_direction",
        directional,
        "F_t ~ same_defense_as_last_foul + C(since_foul) + " + RICH,
        ["same_defense_as_last_foul"],
    )
    transitions = []
    for game_id, g in primary.groupby("game_id"):
        f = g[g.F_t.eq(1)]
        same = f.defense.eq(f.defense.shift()).iloc[1:]
        c = f.defense.value_counts().to_numpy()
        if len(f) > 1:
            expected = np.sum(c * (c - 1)) / (len(f) * (len(f) - 1))
            transitions.append(
                {
                    "game_id": game_id,
                    "opposite_excess": float(1 - same.mean() - (1 - expected)),
                    "same_share": float(same.mean()),
                    "transitions": len(same),
                }
            )
    td = pd.DataFrame(transitions)
    td.to_csv(OUT / "H4_direction_by_game.csv", index=False)
    study.paired(
        4,
        "opposite-team share above random-mark baseline",
        td,
        "opposite_excess",
        "share difference",
    )
    opportunity = []
    for game_id, g in primary.groupby("game_id", sort=False):
        team = g.home_offense.to_numpy(dtype=int)
        actual_f = g.F_t.to_numpy(dtype=int)
        randomized = np.zeros((500, len(g)), dtype=bool)
        for side in (0, 1):
            slots = np.flatnonzero(team == side)
            count = int(actual_f[slots].sum())
            chosen = np.argsort(study.rng.random((500, len(slots))), axis=1)[:, :count]
            randomized[np.arange(500)[:, None], slots[chosen]] = True
        previous = np.maximum.accumulate(
            np.where(randomized, np.arange(len(g)), -1), axis=1
        )
        previous = np.column_stack([np.full(500, -1), previous[:, :-1]])
        valid = randomized & (previous >= 0)
        opposite = (team[previous.clip(min=0)] != team) & valid
        null = (opposite.sum(axis=1) / valid.sum(axis=1)).mean()
        foul_teams = team[actual_f == 1]
        observed = np.mean(foul_teams[1:] != foul_teams[:-1])
        opportunity.append(
            {
                "game_id": game_id,
                "observed_opposite": observed,
                "opportunity_null": null,
                "excess": observed - null,
            }
        )
    opp = pd.DataFrame(opportunity)
    opp.to_csv(OUT / "H4_opportunity_permutation.csv", index=False)
    study.paired(
        4,
        "opposite-team share above within-team opportunity permutation",
        opp,
        "excess",
        "share difference",
    )
    study.details[4].append(
        {
            "permutations_per_game": 500,
            "baseline": "Shuffle foul indicators only among the same team's actual defensive opportunities, preserving each team's game foul total. This is not full play-style adjustment.",
            "lag_caution": "Defense alternates on most possessions; the lag-conditioned directional coefficient relies on deviations from strict alternation and cannot identify makeup intent.",
        }
    )

    study.model(
        5,
        "margin_interaction",
        primary,
        "F_t ~ L2*close + L2*blowout + " + RICH,
        ["L2:close", "L2:blowout"],
    )
    study.model(
        5,
        "margin_interaction_without_late_strategy",
        nonlate,
        "F_t ~ L2*close + L2*blowout + " + RICH,
        ["L2:close", "L2:blowout"],
    )
    for label, subset in [
        ("close", primary[primary.close.eq(1)]),
        ("blowout", primary[primary.blowout.eq(1)]),
        ("fourth_or_OT", primary[primary.period.ge(4)]),
    ]:
        s = component_stats(subset).sum(numeric_only=True)
        ratio = ((s.f1 + s.c1) / s.n1) / ((s.f0 + s.c0) / s.n0)
        study.record(
            5,
            label + " WMI with original global windows",
            ratio,
            n=len(subset),
            games=subset.game_id.nunique(),
            unit="ratio",
        )
    clean = primary.copy()
    for col in ("F_t", "L_t", "N_t", "M_t"):
        clean[col] = clean["clean_" + col]
    clean["L2"] = clean.L_t
    clean["N2"] = clean.N_t
    s = component_stats(clean).sum(numeric_only=True)
    study.record(
        5,
        "WMI with suspected intentional calls masked throughout windows",
        ((s.f1 + s.c1) / s.n1) / ((s.f0 + s.c0) / s.n0),
        n=len(clean),
        games=clean.game_id.nunique(),
        unit="ratio",
    )

    study.model(
        6,
        "bonus_interaction",
        primary,
        "F_t ~ L2*bonus + "
        + BASE
        + " + prior_rim_attempts + prior_three_attempts + prior_fta",
        ["bonus", "L2:bonus"],
    )
    combined = df[df.year.eq(2024)].copy()
    combined["nonshooting_only"] = (
        combined.F_t.eq(1) & combined.shooting_foul.eq(0)
    ).astype(int)
    study.model(
        7,
        "playoff_interaction",
        combined,
        "F_t ~ L2*postseason + " + RICH,
        ["postseason", "L2:postseason"],
    )
    study.model(
        7,
        "shooting_foul_playoff_interaction",
        combined,
        "shooting_foul ~ L2*postseason + " + RICH,
        ["postseason", "L2:postseason"],
    )
    study.model(
        7,
        "nonshooting_only_playoff_interaction",
        combined,
        "nonshooting_only ~ L2*postseason + " + RICH,
        ["postseason", "L2:postseason"],
    )
    directional_post = combined[combined.since_foul.between(1, 10)]
    study.model(
        7,
        "direction_playoff_interaction",
        directional_post,
        "F_t ~ same_defense_as_last_foul*postseason + C(since_foul) + " + RICH,
        ["same_defense_as_last_foul:postseason"],
    )
    study.model(
        7,
        "close_game_playoff_sequence_interaction",
        combined,
        "F_t ~ L2*postseason*close + " + RICH,
        ["L2:postseason:close"],
    )
    study.model(
        8,
        "home_direction_interaction",
        combined,
        "F_t ~ L2*home_offense + close + postseason + " + RICH,
        ["home_offense", "L2:home_offense"],
    )
    study.model(
        8,
        "home_in_close_games",
        combined[combined.close.eq(1)],
        "F_t ~ L2*home_offense + postseason + " + RICH,
        ["home_offense", "L2:home_offense"],
    )
    return primary


def crowd_hypothesis(study):
    search = pd.read_csv(
        ROOT / "wmi_search_games_2019_2026.csv", dtype={"game_id": str}
    )
    search["date"] = pd.to_datetime(
        search.game_date_et.astype(str), format="mixed", errors="coerce", utc=True
    ).dt.strftime("%Y-%m-%d")
    bubble = (
        search[search.season.eq("2019-20") & search.season_type.eq("Regular Season")]
        .dropna(subset=["WMI"])
        .copy()
    )
    bubble["bubble"] = bubble.date.ge("2020-07-30").astype(int)
    bubble["offense"] = bubble.home_team
    bubble["defense"] = bubble.away_team
    study.model(
        9,
        "bubble_same_season_regular_games",
        bubble,
        "WMI ~ bubble + C(offense) + C(defense)",
        ["bubble"],
        False,
    )
    box = pd.read_csv(CACHE / "box.csv", low_memory=False).drop_duplicates("GAME_ID")
    box["game_id"] = box.GAME_ID.map(gid)
    attendance = search.merge(
        box[["game_id", "ATTENDANCE"]], on="game_id", how="inner"
    ).dropna(subset=["WMI", "ATTENDANCE"])
    attendance["attendance_10k"] = attendance.ATTENDANCE / 10000
    study.model(
        9,
        "recorded_attendance_selected_close_game_archive",
        attendance,
        "WMI ~ attendance_10k + C(season) + C(season_type)",
        ["attendance_10k"],
        False,
    )
    study.details[9].append(
        {
            "bubble_games": int(bubble.bubble.sum()),
            "pre_bubble_games": int(bubble.bubble.eq(0).sum()),
            "attendance_sample_games": len(attendance),
            "zero_recorded_attendance": int(attendance.ATTENDANCE.eq(0).sum()),
            "selection": "The attendance/box-score archive emphasizes L2M qualifying close games; missing attendance is not assumed to mean zero.",
        }
    )
    attendance[["game_id", "season", "WMI", "ATTENDANCE"]].to_csv(
        OUT / "H9_attendance_sample.csv", index=False
    )


def player_event_tables(primary, current_events, prior_events):
    # Fixed before the test season: highest prior-season blocks + steals per
    # appearance, >=40 appearances. This is a defensive-activity proxy, not a
    # claim that these are the thirty best defenders.
    appearances = (
        prior_events[prior_events.personId.gt(0)].groupby("personId").game_id.nunique()
    )
    activity = (
        prior_events[prior_events.actionType.isin(["block", "steal"])]
        .groupby("personId")
        .size()
    )
    ranking = (activity / appearances).loc[appearances.ge(40)].dropna().nlargest(30)
    stars = set(ranking.index.astype(int))
    ranking.rename("prior_blocks_plus_steals_per_appearance").to_csv(
        OUT / "H10_predefined_defenders.csv"
    )
    trouble, draws = [], []
    table_map = {
        k: g.reset_index(drop=True) for k, g in primary.groupby("game_id", sort=False)
    }
    for game_id, ev in current_events.groupby("game_id", sort=False):
        if game_id not in table_map:
            continue
        g = table_map[game_id]
        ev = ev.reset_index(drop=True)
        position = {int(r.source_group): int(r.pos) for r in g.itertuples()}
        for ix, r in ev[ev.counted_def_foul.eq(1)].iterrows():
            pos = position.get(int(r.group))
            if pos is None or pos < 5 or pos + 10 >= len(g):
                continue
            current = g.iloc[pos]
            after = g.iloc[pos + 1 :]
            before = g.iloc[:pos]
            pid = int(r.personId)
            pf = r.player_pf_after
            team = str(r.teamTricode)
            if (
                pid in stars
                and pd.notna(pf)
                and pf in (2, 3, 4, 5)
                and r.remaining > 120
            ):
                eligible = (
                    (pf in (2, 3) and r.period <= 2)
                    or (pf == 4 and r.period <= 3)
                    or pf == 5
                )
                if eligible:
                    # Substitution observed before the next possession starts.
                    between = ev.iloc[ix + 1 :][
                        ev.iloc[ix + 1 :].group.le(int(r.group))
                    ]
                    benched = int(
                        (
                            (between.actionType.eq("substitution"))
                            & (between.subType.eq("out"))
                            & (between.personId.eq(pid))
                        ).any()
                    )
                    pre_opp = before[before.defense.eq(team)].tail(5)
                    post_opp = after[after.defense.eq(team)].head(5)
                    if len(pre_opp) != 5 or len(post_opp) != 5:
                        continue
                    pre_rim = pre_opp.rim_attempts.sum() / max(1, pre_opp.fga.sum())
                    post_rim = post_opp.rim_attempts.sum() / max(1, post_opp.fga.sum())
                    following = g.iloc[pos + 1 : pos + 6]
                    sign = 1 if team == current.home else -1
                    trouble.append(
                        {
                            "game_id": game_id,
                            "player": pid,
                            "pf": int(pf),
                            "period": int(r.period),
                            "remaining": float(r.remaining),
                            "time_scaled": float(current.time_scaled),
                            "own_margin": float(-current.score_diff),
                            "margin": float(current.margin),
                            "benched": benched,
                            "keep": 1 - benched,
                            "threshold": int(pf >= 3),
                            "rim_change": float(post_rim - pre_rim),
                            "opponent_points_change": float(
                                post_opp.own_points.mean() - pre_opp.own_points.mean()
                            ),
                            "net_next5": float(
                                sign
                                * (following.home_points - following.away_points).sum()
                            ),
                        }
                    )
            drawn = r.foulDrawnPersonId
            if pd.notna(drawn) and drawn > 0:
                offense = current.offense
                pre = before[before.offense.eq(offense)].tail(5)
                post = after[after.offense.eq(offense)].head(5)
                if len(pre) < 5 or len(post) < 5:
                    continue
                pre_ev = ev[ev.group.isin(pre.source_group)]
                post_ev = ev[ev.group.isin(post.source_group)]
                pre_shots = pre_ev[pre_ev.personId.eq(drawn) & pre_ev.isFieldGoal.eq(1)]
                post_shots = post_ev[
                    post_ev.personId.eq(drawn) & post_ev.isFieldGoal.eq(1)
                ]
                draws.append(
                    {
                        "game_id": game_id,
                        "player": int(drawn),
                        "pre_fga": len(pre_shots),
                        "post_fga": len(post_shots),
                        "shot_count_change": len(post_shots) - len(pre_shots),
                        "repeat_draw_change": int(
                            (
                                post_ev.counted_def_foul.eq(1)
                                & post_ev.foulDrawnPersonId.eq(drawn)
                            ).sum()
                        )
                        - int(
                            (
                                pre_ev.counted_def_foul.eq(1)
                                & pre_ev.foulDrawnPersonId.eq(drawn)
                            ).sum()
                        ),
                        "rim_share_change": float(
                            post_shots.shotDistance.le(4).mean()
                            - pre_shots.shotDistance.le(4).mean()
                        )
                        if len(pre_shots) and len(post_shots)
                        else np.nan,
                        "three_share_change": float(
                            post_shots.actionType.eq("3pt").mean()
                            - pre_shots.actionType.eq("3pt").mean()
                        )
                        if len(pre_shots) and len(post_shots)
                        else np.nan,
                    }
                )
    return pd.DataFrame(trouble), pd.DataFrame(draws)


def player_hypotheses(study, primary):
    events = pd.read_parquet(CACHE / "cdnnba_2024.events.parquet")
    prior = pd.read_parquet(CACHE / "cdnnba_2023.events.parquet")
    trouble, draws = player_event_tables(primary, events, prior)
    trouble.to_csv(OUT / "H10_H11_player_foul_events.csv", index=False)
    draws.to_csv(OUT / "H12_player_draw_events.csv", index=False)
    high = trouble[trouble.threshold.eq(1)].copy()
    study.model(
        10,
        "substitution_after_third_vs_second_early_foul",
        trouble[trouble.pf.isin([2, 3])],
        "benched ~ threshold + own_margin + margin + time_scaled + C(period)",
        ["threshold"],
    )
    study.paired(
        10,
        "rim-attempt share after minus before trouble",
        high,
        "rim_change",
        "share difference",
    )
    study.paired(
        10,
        "opponent points per possession after minus before trouble",
        high,
        "opponent_points_change",
        "points per possession",
    )
    study.model(
        11,
        "observational_keep_vs_bench",
        high,
        "net_next5 ~ keep + own_margin + margin + time_scaled + C(pf) + C(period) + C(player)",
        ["keep"],
        False,
    )
    study.details[11].append(
        {
            "kept_events": int(high.keep.sum()),
            "benched_events": int(high.benched.sum()),
            "identification": "Unmeasured matchup, player health, coach knowledge and lineup quality can drive selection. The keep coefficient does not identify an optimal substitution policy.",
        }
    )
    for value in (
        "shot_count_change",
        "repeat_draw_change",
        "rim_share_change",
        "three_share_change",
    ):
        study.paired(
            12, value + " next vs previous five offensive possessions", draws, value
        )
    study.details[12].append(
        {
            "all_draw_events": len(draws),
            "events_with_shots_before_and_after": int(
                draws.rim_share_change.notna().sum()
            ),
            "selection": "Shot-mix tests condition on the player shooting in both windows. No video-level drives, contact legality or noncall labels are inferred.",
        }
    )


def rule_hypothesis(study, df):
    all_rows = []
    for year in (2021, 2022):
        ev = pd.read_parquet(CACHE / f"cdnnba_{year}.events.parquet")
        # Common pre/post taxonomy: descriptor containing 'take'. Do not compare
        # absent pre-rule 'transition take' labels with new post-rule labels.
        take = ev[
            ev.counted_def_foul.eq(1)
            & ev.descriptor.fillna("").str.contains("take")
            & ~(ev.period.ge(4) & ev.remaining.le(120))
        ]
        counts = take.groupby("game_id").size()
        games = (
            df[df.year.eq(year)]
            .groupby("game_id")
            .agg(
                possessions=("pos", "size"),
                date=("date", "first"),
                post=("year", "first"),
            )
        )
        games["post"] = (year == 2022) * 1
        games["count"] = counts.reindex(games.index, fill_value=0)
        games["exposure"] = np.log(games.possessions)
        all_rows.append(games.reset_index())
        # Descriptive points in the foul possession, not causal foul value.
        p = df[df.year.eq(year)]
        join = take[["game_id", "group"]].merge(
            p[["game_id", "source_group", "own_points"]],
            left_on=["game_id", "group"],
            right_on=["game_id", "source_group"],
        )
        study.record(
            13,
            f"{year}-{str(year + 1)[-2:]} own points on take-foul possessions",
            join.own_points.mean(),
            n=len(join),
            games=join.game_id.nunique(),
            unit="points",
        )
    data = pd.concat(all_rows, ignore_index=True)
    data.to_csv(OUT / "H13_take_foul_game_counts.csv", index=False)
    fit = smf.glm(
        "count ~ post", data=data, offset=data.exposure, family=sm.families.Poisson()
    ).fit(cov_type="HC1")
    lo, hi = fit.conf_int().loc["post"]
    study.record(
        13,
        "post/pre common take-label rate per possession",
        np.exp(fit.params["post"]),
        np.exp(lo),
        np.exp(hi),
        fit.pvalues["post"],
        len(data),
        len(data),
        "rate ratio",
    )
    for post, g in data.groupby("post"):
        study.details[13].append(
            {
                "post_rule": int(post),
                "games": len(g),
                "take_events": int(g["count"].sum()),
                "rate_per_1000_possessions": float(
                    1000 * g["count"].sum() / g.possessions.sum()
                ),
            }
        )
    data["months_from_rule"] = (
        pd.to_datetime(data.date) - pd.Timestamp("2022-10-18")
    ).dt.days / 30
    segmented = smf.glm(
        "count ~ post*months_from_rule",
        data=data,
        offset=data.exposure,
        family=sm.families.Poisson(),
    ).fit(cov_type="HC1")
    lo, hi = segmented.conf_int().loc["post"]
    study.record(
        13,
        "segmented trend rule-date level ratio",
        np.exp(segmented.params["post"]),
        np.exp(lo),
        np.exp(hi),
        segmented.pvalues["post"],
        len(data),
        len(data),
        "rate ratio",
    )
    study.details[13].append(
        {
            "segmented_formula": "Poisson count ~ post * months_from_rule; offset log(possessions); HC1 game-level uncertainty",
            "identification": "Two seasons, with an offseason interruption and no unaffected control group. Changes in labels, rules and strategy can confound policy attribution.",
        }
    )


def challenge_hypothesis(study, primary):
    mobile = read_archive("datanba_2024", low_memory=False)
    labels = mobile[
        mobile.etype.eq(18) & mobile.de.fillna("").str.contains("Challenge", case=False)
    ].copy()
    labels["game_id"] = labels.GAME_ID.map(gid)
    labels["success"] = labels.de.str.contains("Overturn", case=False).astype(int)
    labels["elapsed"] = [
        elapsed_seconds(
            int(p), int(str(c).split(":")[0]) * 60 + float(str(c).split(":")[1])
        )
        for p, c in zip(labels.PERIOD, labels.cl)
    ]
    labels = labels.drop_duplicates(["game_id", "evt"])
    rows = []
    table_map = {k: g.reset_index(drop=True) for k, g in primary.groupby("game_id")}
    for game_id, ls in labels.groupby("game_id"):
        if game_id not in table_map:
            continue
        g = table_map[game_id]
        used = set()
        for r in ls.itertuples():
            # First possession strictly starting after the replay clock. The
            # reviewed/corrected possession itself is excluded from the outcome.
            idx = np.flatnonzero(g.start_elapsed.to_numpy() > r.elapsed)
            if not len(idx):
                continue
            start = int(idx[0])
            if start < 10 or start + 10 > len(g) or start in used:
                continue
            used.add(start)
            # Exclude windows with another challenge to reduce contamination.
            if (
                (ls.elapsed > r.elapsed) & (ls.elapsed < g.iloc[start + 9].end_elapsed)
            ).any():
                continue
            pre = g.iloc[start - 10 : start]
            post = g.iloc[start : start + 10]
            eligible = g[
                (g.period.eq(post.period.iloc[0]))
                & (g.pos.ge(10))
                & (g.pos.le(len(g) - 10))
            ].copy()
            for q in ls.itertuples():
                eligible = eligible[(eligible.start_elapsed - q.elapsed).abs() > 240]
            if eligible.empty:
                continue
            distance = (
                ((eligible.margin - post.margin.iloc[0]) / 10) ** 2
                + ((eligible.remaining - post.remaining.iloc[0]) / 180) ** 2
                + ((eligible.L2 - post.L2.iloc[0]) * 0.5) ** 2
            )
            control = int(eligible.loc[distance.idxmin(), "pos"])
            if distance.min() > 4:
                continue
            cpre = g.iloc[control - 10 : control]
            cpost = g.iloc[control : control + 10]
            diff = float(post.F_t.mean() - pre.F_t.mean())
            c_diff = float(cpost.F_t.mean() - cpre.F_t.mean())
            rows.append(
                {
                    "game_id": game_id,
                    "event": r.evt,
                    "success": r.success,
                    "change": diff,
                    "control_change": c_diff,
                    "difference_in_differences": diff - c_diff,
                    "period": int(post.period.iloc[0]),
                    "margin": float(post.margin.iloc[0]),
                    "remaining": float(post.remaining.iloc[0]),
                }
            )
    data = pd.DataFrame(rows)
    data.to_csv(OUT / "H14_matched_challenges.csv", index=False)
    study.paired(
        14,
        "successful challenge versus matched no-challenge change",
        data[data.success.eq(1)],
        "difference_in_differences",
        "foul probability difference",
    )
    study.model(
        14,
        "successful_vs_unsuccessful_challenges",
        data,
        "difference_in_differences ~ success + margin + remaining + C(period)",
        ["success"],
        False,
    )
    study.details[14].append(
        {
            "labeled_challenges": len(labels),
            "labeled_successes": int(labels.success.sum()),
            "matched_challenges": len(data),
            "matched_successes": int(data.success.sum()),
            "scope": "All challenged call types, including out-of-bounds; original foul-call-only identification is not validated.",
        }
    )


def crew_hypothesis(study, df, games):
    # Crew composition is an unordered triple of the actual assigned officials.
    stats = component_stats(df[df.postseason.eq(0)])
    data = games.merge(stats, on="game_id", how="inner")
    data = data[data.crew.map(lambda x: len(x.split("|")) == 3 and "nan" not in x)]
    data["log_immediate"] = np.log(data.immediate.replace(0, np.nan))
    agg = (
        data.groupby(["year", "crew"])
        .agg(
            games=("game_id", "size"),
            log_immediate=("log_immediate", "mean"),
            mean_WMI=("WMI", "mean"),
        )
        .reset_index()
    )
    agg.to_csv(OUT / "H15_crew_season_profiles.csv", index=False)
    pairs = []
    # No exact triple has >=2 games in BOTH adjacent years. Use all repeated
    # triples as an explicitly noisy exploratory test, not a reliable ranking.
    for year in (2021, 2022, 2023, 2024):
        previous = agg[(agg.year.eq(year - 1)) & agg.games.ge(1)]
        current = agg[(agg.year.eq(year)) & agg.games.ge(1)]
        match = previous.merge(
            current, on="crew", suffixes=("_previous", "_current")
        ).dropna(subset=["log_immediate_previous", "log_immediate_current"])
        for r in match.itertuples():
            pairs.append(
                {
                    "year": year,
                    "crew": r.crew,
                    "previous": r.log_immediate_previous,
                    "current": r.log_immediate_current,
                }
            )
    paired = pd.DataFrame(pairs)
    paired.to_csv(OUT / "H15_repeated_crew_pairs.csv", index=False)
    if len(paired) >= 10:
        corr = float(spearmanr(paired.previous, paired.current).statistic)
        # Resample complete crew identities, preserving repeated years.
        crew_ids = paired.crew.unique()
        draws = []
        for _ in range(1000):
            sampled = study.rng.choice(crew_ids, size=len(crew_ids), replace=True)
            v = pd.concat(
                [paired[paired.crew.eq(c)] for c in sampled], ignore_index=True
            )
            draws.append(spearmanr(v.previous, v.current).statistic)
        lo, hi = np.nanquantile(draws, [0.025, 0.975])
        se = np.nanstd(draws, ddof=1)
        study.record(
            15,
            "same assigned crew year-to-year log-immediate correlation",
            corr,
            lo,
            hi,
            2 * norm.sf(abs(corr / se)),
            len(paired),
            len(crew_ids),
            "Spearman correlation",
        )
    study.details[15].append(
        {
            "matched_crew_year_pairs": len(paired),
            "distinct_repeated_crews": int(paired.crew.nunique()) if len(paired) else 0,
            "minimum_games_per_crew_per_year": 1,
            "pairs_with_at_least_two_games_in_each_year": 0,
            "coverage_adaptation": "A three-game minimum produced no pairs. This all-repeat sensitivity was chosen after inspecting coverage and is exploratory; it cannot measure latent crew reliability precisely.",
            "selection": "Exact crews recur sparsely. No official is assigned another member’s calls and no inference about intent is made.",
        }
    )


def scoring_hypothesis(study, primary):
    # Prediction at the start of t: L2 is past-only; targets are t+1..t+5.
    # Current F, N and final WMI are never predictors of these outcomes.
    data = primary.dropna(
        subset=["future_net5", "future_fta5", "future_turnovers5", "future_rim5"]
    ).copy()
    for target in [
        "future_net5",
        "future_fta5",
        "future_turnovers5",
        "future_rim5",
        "future_clock_seconds5",
    ]:
        study.model(16, target, data, target + " ~ L2 + " + RICH, ["L2"], False)


def add_pregame_strength(games):
    ratings = defaultdict(lambda: 1500.0)
    rows = []
    previous_year = None
    for r in games.sort_values(["date", "game_id"]).itertuples():
        if previous_year is not None and r.year != previous_year:
            ratings = {
                team: 1500 + (score - 1500) * 0.75 for team, score in ratings.items()
            }
            ratings = defaultdict(lambda: 1500.0, ratings)
        diff = ratings[r.home] - ratings[r.away]
        rows.append(
            {
                "game_id": r.game_id,
                "elo_diff": diff,
                "home_win": int(r.home_score > r.away_score),
            }
        )
        expected = 1 / (1 + 10 ** (-(diff + 65) / 400))
        update = 20 * ((r.home_score > r.away_score) - expected)
        ratings[r.home] += update
        ratings[r.away] -= update
        previous_year = r.year
    return pd.DataFrame(rows)


def win_features(frame):
    frame = frame.copy()
    frame["lead_scaled"] = frame.home_margin / np.sqrt(frame.reg_remaining / 60 + 1)
    frame["time_fraction"] = frame.start_elapsed / 2880
    frame["lead_time"] = frame.home_margin * frame.time_fraction
    return frame


def probability_metrics(y, p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(
        np.mean(bins == b) * abs(np.mean(y[bins == b]) - np.mean(p[bins == b]))
        for b in range(10)
        if np.any(bins == b)
    )
    return {
        "roc_auc": roc_auc_score(y, p),
        "average_precision": average_precision_score(y, p),
        "brier": brier_score_loss(y, p),
        "log_loss": log_loss(y, p),
        "ece_10_fixed_bins": ece,
    }


def win_hypothesis(study, df, games):
    strength = add_pregame_strength(games)
    strength.to_csv(OUT / "pregame_elo.csv", index=False)
    regular = df[df.postseason.eq(0) & df.period.le(4)].merge(
        strength, on="game_id", validate="many_to_one"
    )
    snapshots = []
    for _, g in regular.groupby("game_id", sort=False):
        for threshold in range(0, 2880, 180):
            valid = g[g.start_elapsed.ge(threshold)]
            if len(valid):
                snapshots.append(valid.iloc[0])
    data = win_features(pd.DataFrame(snapshots).drop_duplicates(["game_id", "pos"]))
    train = data[data.year.le(2022)]
    validation = data[data.year.eq(2023)]
    test = data[data.year.eq(2024)].copy()
    state = [
        "home_margin",
        "lead_scaled",
        "lead_time",
        "time_fraction",
        "elo_diff",
        "home_offense",
    ]
    history = ["L2", "recent_count", "live_log_wmi", "bonus", "team_pf"]
    predictions = {}
    models = {}
    metric_rows = []
    for label, features in [
        ("state_and_strength", state),
        ("state_strength_and_fouls", state + history),
    ]:
        candidates = []
        for penalty in (0.1, 1, 10):
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(C=penalty, max_iter=500, random_state=SEED),
            )
            model.fit(train[features], train.home_win)
            loss = log_loss(
                validation.home_win, model.predict_proba(validation[features])[:, 1]
            )
            candidates.append((loss, penalty))
        loss, penalty = min(candidates)
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=penalty, max_iter=500, random_state=SEED),
        )
        refit = pd.concat([train, validation])
        model.fit(refit[features], refit.home_win)
        probability = model.predict_proba(test[features])[:, 1]
        predictions[label] = probability
        models[label] = model
        metric_rows.append(
            {
                "model": label,
                "C": penalty,
                "validation_log_loss": loss,
                **probability_metrics(test.home_win.to_numpy(), probability),
            }
        )
        test["p_" + label] = probability
    pd.DataFrame(metric_rows).to_csv(OUT / "H17_prediction_metrics.csv", index=False)
    base = predictions["state_and_strength"]
    plus = predictions["state_strength_and_fouls"]
    y = test.home_win.to_numpy()
    test["brier_difference"] = (y - plus) ** 2 - (y - base) ** 2
    test["log_loss_difference"] = -(y * np.log(plus) + (1 - y) * np.log(1 - plus)) + (
        y * np.log(base) + (1 - y) * np.log(1 - base)
    )
    study.paired(
        17,
        "added foul features: held-out log loss change",
        test,
        "log_loss_difference",
        "loss change; negative improves",
    )
    study.paired(
        17,
        "added foul features: held-out Brier change",
        test,
        "brier_difference",
        "loss change; negative improves",
    )
    test[
        [
            "game_id",
            "pos",
            "home_win",
            "p_state_and_strength",
            "p_state_strength_and_fouls",
            "brier_difference",
            "log_loss_difference",
        ]
    ].to_csv(OUT / "H17_held_out_predictions.csv", index=False)
    study.details[17].append(
        {
            "train_seasons": "2020-21 to 2022-23",
            "validation_season": "2023-24",
            "test_season": "2024-25",
            "test_games": int(test.game_id.nunique()),
            "snapshots": len(test),
            "snapshots_per_game_max": 16,
            "state_features": state,
            "extra_features": history,
            "metrics": metric_rows,
            "elo": "Initial 1500; K=20; home advantage=65; 25% offseason shrinkage, updated only after earlier games.",
        }
    )
    # Supplemental H18: state-model movement through a foul possession. This
    # includes scoring/clock consequences and is not the causal value of a call.
    final = regular[regular.year.eq(2024)].copy()
    before = win_features(final)
    after = final.copy()
    after["home_margin"] = after.home_margin_end
    after["start_elapsed"] = after.end_elapsed
    after["reg_remaining"] = (2880 - after.end_elapsed).clip(lower=0)
    after = win_features(after)
    after["home_offense"] = 1 - after.home_offense
    model = models["state_and_strength"]
    final["foul_wp_movement"] = (
        np.abs(
            model.predict_proba(after[state])[:, 1]
            - model.predict_proba(before[state])[:, 1]
        )
        * final.F_t
    )
    summary = final.groupby("game_id").agg(
        foul_volume=("foul_count", "sum"), foul_wp_movement=("foul_wp_movement", "sum")
    )
    final["home_fouls"] = final.foul_count * (1 - final.home_offense)
    final["away_fouls"] = final.foul_count * final.home_offense
    final["home_fta"] = final.fta * final.home_offense
    final["away_fta"] = final.fta * (1 - final.home_offense)
    sums = final.groupby("game_id")[
        ["home_fouls", "away_fouls", "home_fta", "away_fta"]
    ].sum()
    summary["abs_foul_difference"] = (sums.home_fouls - sums.away_fouls).abs()
    summary["abs_fta_difference"] = (sums.home_fta - sums.away_fta).abs()
    summary = summary.join(
        component_stats(df[df.year.eq(2024) & df.postseason.eq(0)]).set_index(
            "game_id"
        )[["WMI"]]
    ).dropna()
    summary.to_csv(OUT / "H18_volume_consequence_comparison.csv")
    for col in [
        "foul_volume",
        "abs_foul_difference",
        "abs_fta_difference",
        "foul_wp_movement",
    ]:
        values = summary[["WMI", col]].to_numpy()
        point = spearmanr(values[:, 0], values[:, 1]).statistic
        samples = [
            spearmanr(
                (v := values[study.rng.integers(0, len(values), len(values))])[:, 0],
                v[:, 1],
            ).statistic
            for _ in range(1000)
        ]
        lo, hi = np.quantile(samples, [0.025, 0.975])
        study.record(
            18,
            "WMI versus " + col,
            point,
            lo,
            hi,
            spearmanr(values[:, 0], values[:, 1]).pvalue,
            len(values),
            len(values),
            "Spearman correlation",
        )


def save_study(study):
    results = pd.DataFrame(study.results)
    results["q_value_bh"] = np.nan
    tested = results.p_value.notna()
    if tested.any():
        results.loc[tested, "q_value_bh"] = multipletests(
            results.loc[tested, "p_value"], method="fdr_bh"
        )[1]
    results.to_csv(OUT / "all_hypothesis_results.csv", index=False)

    # JSON nulls, not nonstandard NaN/Infinity literals.
    def safe(obj):
        if isinstance(obj, dict):
            return {str(k): safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [safe(v) for v in obj]
        if isinstance(obj, np.generic):
            obj = obj.item()
        if isinstance(obj, float) and not math.isfinite(obj):
            return None
        return obj

    (OUT / "analysis_details.json").write_text(
        json.dumps(safe(dict(study.details)), indent=2, allow_nan=False) + "\n"
    )
    (OUT / "analysis_failures.json").write_text(
        json.dumps(study.failures, indent=2) + "\n"
    )
    return results


def run_study():
    paths = sorted(CACHE.glob("*.poss.parquet"))
    df = add_research_outcomes(
        pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    )
    games = pd.concat(
        [
            pd.read_csv(p, dtype={"game_id": str})
            for p in sorted(OUT.glob("cdnnba*_games.csv"))
        ],
        ignore_index=True,
    )
    # Four archived games contain backward source clocks (including a late memo
    # and replay/shot ordering inconsistencies). Quarantine entire games rather
    # than silently rewriting clocks or compressing their possession sequences.
    clock_anomalies = df[df.end_elapsed.lt(df.start_elapsed)].copy()
    clock_anomalies[
        [
            "game_id",
            "year",
            "pos",
            "period",
            "source_group",
            "start_elapsed",
            "end_elapsed",
        ]
    ].to_csv(OUT / "quarantined_clock_events.csv", index=False)
    quarantined = set(clock_anomalies.game_id)
    df = df[~df.game_id.isin(quarantined)].copy()
    games = games[~games.game_id.isin(quarantined)].copy()
    study = Study()
    for label, operation in [
        ("H1-H8", lambda: main_hypotheses(study, df, games)),
        ("H9", lambda: crowd_hypothesis(study)),
        (
            "H10-H12",
            lambda: player_hypotheses(
                study, df[df.year.eq(2024) & df.postseason.eq(0)]
            ),
        ),
        ("H13", lambda: rule_hypothesis(study, df)),
        (
            "H14",
            lambda: challenge_hypothesis(
                study, df[df.year.eq(2024) & df.postseason.eq(0)]
            ),
        ),
        ("H15", lambda: crew_hypothesis(study, df, games)),
        (
            "H16",
            lambda: scoring_hypothesis(
                study, df[df.year.eq(2024) & df.postseason.eq(0)]
            ),
        ),
        ("H17-H18", lambda: win_hypothesis(study, df, games)),
    ]:
        print("analysis start", label, flush=True)
        try:
            operation()
        except Exception as exc:
            import traceback

            traceback.print_exc()
            study.failures.append({"section": label, "error": repr(exc)})
        save_study(study)
        print("analysis saved", label, "tests", len(study.results), flush=True)
    audit_study(study, df, games)
    build_report()
    return study, df, games


def audit_study(study, df, games):
    """Fail closed on missing sections, incomplete schedules, or score errors."""
    expected = {
        (2020, 0): 1080,
        (2021, 0): 1230,
        (2022, 0): 1230,
        (2023, 0): 1230,
        (2024, 0): 1230,
        (2024, 1): 84,
    }
    inventory = pd.concat(
        [
            pd.read_csv(p, dtype={"game_id": str})
            for p in sorted(OUT.glob("cdnnba*_games.csv"))
        ]
    )
    coverage = inventory.groupby(["year", "postseason"]).size().to_dict()
    retained = games.groupby(["year", "postseason"]).size().to_dict()
    quarantined = sorted(set(inventory.game_id) - set(games.game_id))
    scores = (
        df.groupby("game_id")[["home_points", "away_points"]]
        .sum()
        .join(games.set_index("game_id")[["home_score", "away_score"]])
    )
    search_path = ROOT / "wmi_search_games_2019_2026.csv"
    search = pd.read_csv(search_path, dtype={"game_id": str})
    joined = games.merge(search, on="game_id", suffixes=("_research", "_project"))
    known = joined.dropna(subset=["home_score_project", "away_score_project"])
    results = pd.DataFrame(study.results)
    checks = {
        "all_six_source_schedules_complete": coverage == expected,
        "all_clock_anomaly_games_quarantined": quarantined
        == sorted(
            pd.read_csv(
                OUT / "quarantined_clock_events.csv", dtype={"game_id": str}
            ).game_id.unique()
        ),
        "all_18_sections_have_results": set(results.hypothesis)
        == {f"H{i}" for i in range(1, 19)},
        "no_analysis_failures": not study.failures,
        "unique_possession_keys": not df.duplicated(["game_id", "pos"]).any(),
        "scores_reconcile_every_game": bool(
            np.allclose(scores.home_points, scores.home_score)
            and np.allclose(scores.away_points, scores.away_score)
        ),
        "no_negative_scoring_deltas": not (
            df.home_points.lt(0) | df.away_points.lt(0)
        ).any(),
        "no_negative_possession_durations": not df.end_elapsed.lt(
            df.start_elapsed
        ).any(),
        "known_project_scores_match": bool(
            (
                known.home_score_research.eq(known.home_score_project)
                & known.away_score_research.eq(known.away_score_project)
            ).all()
        ),
        "project_home_away_match": bool(
            (joined.home.eq(joined.home_team) & joined.away.eq(joined.away_team)).all()
        ),
        "finite_tested_estimates_and_intervals": bool(
            np.isfinite(
                results.loc[
                    results.p_value.notna(), ["estimate", "ci_low", "ci_high"]
                ].to_numpy()
            ).all()
        ),
    }
    audit = {
        "checks": {k: bool(v) for k, v in checks.items()},
        "games": len(games),
        "source_games": len(inventory),
        "quarantined_games": quarantined,
        "possessions": len(df),
        "known_project_scores_compared": len(known),
        "source_schedule_scores_missing": int(joined.home_score_project.isna().sum()),
        "period_boundaries_added_vs_ownership_only": int(games.period_splits.sum()),
        "local_schedule_sha256": hashlib.sha256(search_path.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coverage": [
            {
                "season": f"{y}-{str(y + 1)[-2:]}",
                "type": "Playoffs" if p else "Regular season",
                "games": n,
                "retained_games": retained[(y, p)],
            }
            for (y, p), n in coverage.items()
        ],
    }
    (OUT / "run_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    if not all(checks.values()):
        raise AssertionError({k: v for k, v in checks.items() if not v})


def build_report():
    results = pd.read_csv(OUT / "all_hypothesis_results.csv")
    details = json.loads((OUT / "analysis_details.json").read_text())
    audit = json.loads((OUT / "run_audit.json").read_text())

    def number(x):
        if pd.isna(x):
            return "—"
        return f"{x:.3g}" if 0 < abs(x) < 0.001 else f"{x:.5f}".rstrip("0").rstrip(".")

    def table(rows):
        cluster_label = "crews" if rows.hypothesis.eq("H15").all() else "games"
        lines = [
            f"| Test | Estimate | 95% CI | Raw p | BH q | Observations / {cluster_label} | Unit |",
            "|---|---:|---|---:|---:|---:|---|",
        ]
        for r in rows.itertuples():
            ci = (
                "—"
                if pd.isna(r.ci_low)
                else f"[{number(r.ci_low)}, {number(r.ci_high)}]"
            )
            unit = (
                "probability difference" if r.unit == "probability points" else r.unit
            )
            lines.append(
                f"| {r.test} | {number(r.estimate)} | {ci} | {number(r.p_value)} | {number(r.q_value_bh)} | {r.n:,} / {r.games:,} | {unit} |"
            )
        return "\n".join(lines)

    sections = {
        1: (
            "Does recent foul history still matter after accounting for basketball context?",
            "Fitted a binomial logistic model of current defensive-foul occurrence on the previous-two-possession indicator. Controls are signed score difference, absolute margin, remaining regulation time, quarter/OT, offense and defense team, home offense, reconstructed bonus, and rim attempts, three-point attempts and free throws in the previous five global possessions. Repeated the fit after excluding every possession in the likely intentional-fouling state, whether or not it actually contained a foul. A within-game linear probability sensitivity absorbs fixed game and assigned-crew levels.",
            "Small negative dependence survives the measured controls: a recent foul is associated with lower, not higher, current foul probability. The standardized probability change is about −0.64 percentage points. This supports dependence, not positive self-excitation or referee bias.",
            "Partial implementation of the originally proposed full model: these are team fixed effects and game-clustered errors, plus a game-fixed-effect sensitivity—not hierarchical logistic random effects. No validated five-player lineups, drives, matchup tracking, or current legal-contact opportunities are available. Past shot counts are imperfect style proxies. H1 was previously attempted with fewer controls; it was rerun here.",
        ),
        2: (
            "Is WMI driven by immediate occurrence or by future continuation?",
            "Decomposed the two-possession ratio exactly into immediate persistence p1/p0 and continuation (1+q1)/(1+q0). Resampled complete games 1,000 times to estimate uncertainty. The displayed combined ratio uses pooled sufficient statistics for this research diagnostic, not the average of game WMI and not a replacement public season metric.",
            "Immediate persistence is below one, while continuation is slightly above one. The immediate component dominates, putting the combined ratio just below one. Calling all three numbers positive ‘momentum’ would obscure the result.",
            "These are unadjusted descriptive components with pointwise bootstrap intervals, not independently validated causal mechanisms. One game has an undefined conditional continuation component because a required foul count is zero; its sufficient statistics remain usable in the pooled estimate. Previously run; now rerun with the audited period boundaries.",
        ),
        3: (
            "Does the sequence effect fade smoothly with possession distance?",
            "Computed 1-, 2-, 3-, 5-, and 10-possession versions with whole-game bootstrap intervals. Also jointly modeled the five individual foul lags with the H1 context controls.",
            "The pattern does not decay monotonically. Lag two is negative and lag three positive; the broad ten-possession ratio is elevated. A single simple decay story is not supported.",
            "Longer windows change both recent-history exposure and future continuation. They also mix longer-lasting game conditions. They are not direct estimates of a causal decay kernel. The individual-lag regression, rather than comparisons of overlapping ratio intervals, is the formal adjusted test. Previously run; rerun here.",
        ),
        4: (
            "Does the next foul tend to return to the same team or move to its opponent?",
            "Compared observed transitions with two baselines: randomly rearranged team marks among foul events, and 500 within-game permutations of foul indicators among each team's actual defensive possession slots. The second preserves each team's foul total and its opportunities. Separately fitted current foul probability on whether the defense committed the last foul, conditioning on gap 1–10 and H1 controls.",
            "The raw random-mark comparison shows about five percentage points of excess opposite-team transitions. After preserving actual defensive opportunities, the excess is only about 0.83 percentage points, still statistically detectable. The lag-conditioned context model does not show a clear same-team effect. Thus the small residual is baseline-sensitive, not proof of makeup calls.",
            "The opportunity permutation controls defensive slots and team game totals, not changing shot opportunities. The adjusted direction coefficient is identified largely by departures from strict possession alternation; this limits its interpretation. Neither test identifies intentional balancing or call accuracy. Previously run with a simpler baseline; the opportunity-preserving test is new.",
        ),
        5: (
            "Does sequencing differ in close games versus blowouts?",
            "Defined close as pre-possession margin ≤5 and blowout as ≥15, with margins 6–14 as reference. Tested interactions with L2 both before and after excluding all likely intentional-fouling states. Also summarized close, blowout, fourth-quarter/OT, and masked-intentional-call ratios without compressing the possession axis.",
            "The adjusted close-game and blowout interactions do not establish different sequencing effects. Raw subgroup ratios differ, but those differences are not equivalent to a significant adjusted interaction.",
            "The intentional-fouling heuristic is Q4/OT with ≤35 seconds and offense ahead by >3, or ≤15 seconds and offense ahead by ≥1. It is a state-based proxy, not a validated intentional-foul label. The main sensitivity excludes all eligible observations rather than selectively deleting only foul outcomes. Previously run; the exclusion design was corrected here.",
        ),
        6: (
            "Does entering the penalty change the effect of recent fouls?",
            "Reconstructed the defending team's pre-event foul quota separately for each period, including the final-two-minute rule and OT quota, then tested L2 × bonus. Offensive, technical, and double-personal fouls do not consume the reconstructed normal quota.",
            "Bonus status is associated with a lower baseline foul probability in the fitted model, but the bonus-by-history interaction does not establish modified momentum. A baseline bonus association is not evidence for the interaction hypothesis.",
            "Bonus is endogenous to earlier fouls and game behavior. Public foul classifications can miss special-case penalties. This is a reconstruction, not a feed of official live penalty flags, and cannot isolate defender restraint from offensive strategy or whistle thresholds. Newly executed.",
        ),
        7: (
            "Do playoff whistle dynamics differ?",
            "Compared all 84 archived 2025 playoff games with 1,230 regular-season games. Fitted postseason differences and sequence interactions for any defensive foul, shooting-foul possessions, and nonshooting-only foul possessions. Added a directional interaction and a close-game × postseason × recent-history interaction.",
            "The postseason baseline foul odds are higher in this comparison, especially for nonshooting-only fouls. The immediate-history, directional, shooting/nonshooting sequence, and close-game sequence interactions do not establish a different playoff momentum mechanism.",
            "One postseason is not a universal playoff effect. Playoff team selection, matchups, tactical adjustments and series dependence remain; errors are clustered by game, not by series. Close margin is only a leverage proxy. The last 18 playoff home/date assignments came from the existing project schedule because the separate referee-assignment archive ends earlier. No officials were invented. Previously analyzed at game level; the possession-level comparisons are new.",
        ),
        8: (
            "Do home teams have more favorable dynamic foul patterns or call accuracy?",
            "Modeled defensive-foul probability when the offense is home, its interaction with recent history, and the same effects in close games. Included regular season/playoffs and H1 context controls.",
            "The home-offense baseline association is small (odds ratio about 1.029) and survives the global q<0.05 threshold. However, there is no clear home-specific sequence interaction or strengthened close-game effect. A small baseline drawing-fouls association is different from dynamic home whistle momentum.",
            "This measures receiving a counted defensive foul, not whether that foul was correct. A home team drawing more fouls may reflect play style. No correctness/noncall labels were joined, and this is not a complete directional-residual or accuracy study. Previously partial; now expanded with context-adjusted sequence interactions.",
        ),
        9: (
            "Does crowd presence change sequencing?",
            "Used stored game-level WMI for 88 bubble and 971 pre-bubble regular-season games in 2019–20, adjusting for home and away team identities. Separately regressed stored WMI on recorded attendance per 10,000 spectators with season/game-type controls in the box-score archive's 2,111 matched games.",
            "Neither comparison establishes an attendance or bubble sequencing association. The uncertainty leaves room for effects in either direction.",
            "This is partial: there is no reliable three-way normal/restricted/no-crowd classification. Missing attendance was never set to zero. The attendance archive disproportionately covers L2M-qualifying close games. Bubble selection, neutral courts, schedule restart and different teams confound a causal crowd claim. This section uses legacy stored WMI and therefore does not share the rich-CDN research parser used by most other sections. The prior bubble comparison was rerun; the recorded-attendance analysis is new.",
        ),
        10: (
            "Does foul trouble for an important defender change opponent strategy?",
            "Predefined 30 high-defensive-activity players using prior-season blocks plus steals per event-observed appearance, requiring at least 40 appearances. Examined early second/third fouls, fourth fouls through Q3, and fifth fouls, all with >2 minutes left in the period. Tested immediate substitutions after third versus second early fouls and before/after opponent rim share and points per possession over five opponent possessions.",
            "Coaches are much more likely to substitute after an early third foul than a second. The observed rim-attempt share does not clearly change; the opponent scoring estimate is imprecise. Thus substitution response is supported, but the proposed attack-the-defender mechanism is not established.",
            "Blocks/steals activity is a reproducible proxy, not a validated list of stars or defensive impact. No drives, contests or matchup-level targeting were measured. The rim/efficiency comparison is before/after without matched no-trouble controls, and substitutions change who is on the floor. Newly executed.",
        ),
        11: (
            "Are coaches systematically too conservative in benching foul-troubled players?",
            "Compared keeping versus immediately benching the predefined defenders after qualifying third/fourth/fifth fouls. Modeled the player's team net points over the next five global possessions with player, personal-foul-count and period indicators plus score/time controls.",
            "The keep-versus-bench estimate is imprecise and does not demonstrate that either policy is better. This analysis cannot determine whether coaches are too conservative.",
            "This is an executed observational comparison, not an optimal-policy test. Coach knowledge, injuries, matchup, replacement quality and lineups confound the decision; later returns were not modeled. A credible causal answer requires validated lineup histories and a defensible policy-identification design. Newly executed, with causal identification explicitly unresolved.",
        ),
        12: (
            "Do offensive players change behavior after drawing a foul?",
            "For identified foul-drawing players, compared the next and previous five team offensive possessions, excluding the triggering possession. Measured player shot counts, repeat foul draws, rim share and three-point share, with game-cluster bootstrap uncertainty. Shot-mix comparisons require the player to shoot in both windows.",
            "There is a tiny decrease in shot counts and a tiny increase in subsequent repeated foul draws. The shot-location shifts are not clearly established. This is not strong evidence of a large behavioral momentum mechanism.",
            "No drives, disputed noncalls, unfavorable rulings or legal-contact judgments were inferred. Fatigue, substitutions and selection into a foul event can create before/after differences. The 12,604 shot-mix events are a selected subset of the 38,296 draw events, not all player possessions. Newly executed.",
        ),
        13: (
            "Did the 2022 transition-take-foul rule change frequency and value?",
            "Compared 2021–22 with 2022–23 using the common descriptor containing ‘take’, excluding the last two minutes of Q4/OT. Estimated a Poisson rate ratio with possession exposure and a segmented time-trend sensitivity at October 18, 2022. Also reported points scored on the labeled take-foul possessions.",
            "Take-labeled defensive fouls declined sharply after the rule change. Observed points on those possessions were higher afterward. The frequency result is strong as a descriptive pre/post association; causal value is not identified.",
            "The denominator is all possessions, not transition opportunities. The common label includes more than perfectly classified transition-take events; documentation or classification could change. Two seasons and an offseason gap, with no unaffected comparison group, cannot isolate the rule from concurrent changes. The points comparison is not expected points conceded relative to a no-foul counterfactual, and retained-possession tagging can affect aggregation. Newly executed.",
        ),
        14: (
            "Does a successful challenge change the next whistle pattern?",
            "Identified explicit Challenge replay decisions in the mobile feed, aligned them to the rich-CDN game clock, and compared foul rates in ten possessions before/after. The reviewed possession was excluded. Matched no-challenge windows within the same game/period on margin, remaining time and recent foul history, excluding nearby challenges. Tested successful-challenge difference-in-differences and successful versus unsuccessful challenges.",
            "Successful challenges are followed by lower foul rates relative to the selected no-challenge windows, but the success-versus-failure contrast does not clearly separate successful challenges from challenges generally. Treat the result as suggestive and design-sensitive.",
            "All reviewed call types are included, not only foul calls. Matching is approximate and challenge timing is strategic. The pre-window can include the disputed incident, encouraging regression to the mean. Windows may overlap; game bootstrap accounts for within-game dependence but does not solve selection or matching bias. Newly executed.",
        ),
        15: (
            "Do exact referee crews have stable sequencing profiles across seasons?",
            "Built unordered triples of assigned officials and each crew-season's mean log immediate-persistence component. Matched exact triples in adjacent seasons and measured Spearman correlation, bootstrapping complete crew identities to preserve repeated years.",
            "The cross-season correlation is about 0.08, with an interval spanning zero. This does not establish observable stability. Because crew-season estimates are extremely noisy, it also cannot support a dependable ranking or rule out stable latent differences.",
            "No exact crew had at least two games in BOTH matched years, so the originally attempted three-game minimum yielded zero pairs. The fallback includes all repeated triples and was chosen after inspecting coverage. Noise attenuates correlations; team/matchup assignment is not randomized. These are crew-game associations, never attribution of another official's calls or evidence about intent. Newly executed with weak measurement reliability.",
        ),
        16: (
            "Does recent foul history predict short-term scoring or style changes?",
            "Used past-only L2 at possession start to model net points, combined free-throw attempts, turnovers, rim attempts and elapsed game-clock seconds over t+1 through t+5. Included H1 controls and game-clustered uncertainty. Censored the final five possessions instead of filling unknown outcomes with zeros.",
            "Recent foul history is associated with roughly 0.033 fewer next-five net points from the current offense's perspective and about 0.35 fewer game-clock seconds over that window. Both are tiny. Free throws show no clear change; turnover and rim-attempt associations do not survive the global q<0.05 threshold. Statistical detectability should not be mistaken for useful forecasting magnitude.",
            "This is an in-sample conditional-association analysis, not an out-of-sample scoring forecast. Five global possessions give unequal offensive opportunities; net points are oriented to the offense at t. FTA, turnovers and rim attempts pool both teams. Game-clock time is a pace proxy, not real elapsed time. Current F_t, future N_t and final WMI are not predictors. Previously not run; newly executed here.",
        ),
        17: (
            "Do live foul-history features improve win-probability predictions?",
            "Trained standardized logistic models on 2020–21 through 2022–23, selected regularization using 2023–24, refit on all training/validation games, and evaluated on held-out 2024–25 games. Sampled up to 16 regulation states per game. The baseline uses score, time, possession and past-updated Elo strength; the augmented model adds L2, recent foul count, bonus/team fouls and a smoothed cumulative WMI using only completed next-two windows.",
            "The augmented model does not improve held-out log loss or Brier score. Both point changes are slightly worse and their game-bootstrap intervals include zero. There is no demonstrated predictive benefit from this feature set and model.",
            "This is a real chronological test of this specification, not a proof that no richer model can benefit. No tracking, active lineups, player foul trouble or advanced sequence architecture was included. Elo starts at 1500, uses K=20 and 65 home-rating points, and shrinks 25% toward 1500 each offseason. Validation chooses C from 0.1, 1 and 10; test games do not choose it. Prior reports had only within-season splits; this test is stronger.",
        ),
        18: (
            "Does high WMI necessarily imply a large officiating impact? (Additional supplied hypothesis.)",
            "Compared full-game research WMI with counted foul volume, absolute foul differential, absolute free-throw differential and summed absolute baseline win-model movement through foul possessions. These comparison quantities use regulation only, matching the win model's domain. Bootstrapped games for Spearman intervals.",
            "WMI has only a weak volume relationship and little relationship to the measured differentials or foul-associated win-probability movement. It is not interchangeable with foul volume or consequence magnitude.",
            "Win-probability movement includes the score/clock/possession changes occurring during a foul possession and assumes a possession switch at its end. It is not the counterfactual causal effect of a call and says nothing about whether a call was correct. Full-game WMI versus regulation consequences is a stated scope mismatch in OT games. Previously attempted; rerun with a chronologically trained state model.",
        ),
    }
    lines = [
        "# Full breakdown of all 17 WMI hypotheses — plus supplied H18",
        "",
        f"Run date: {datetime.now(UTC).date().isoformat()} · Research seed: {SEED}",
        "",
        "## Executive assessment",
        "",
        "All H1–H17 were revisited: earlier analyses were rerun, previously unavailable bonus/player/rule/challenge/crew tests were assembled, and crowd and win-prediction analyses were expanded. The attachment actually lists 18 hypotheses, so H18 is included as an additional section. **Every section has an empirical result; not every original causal claim is identifiable.** This is a separate research package, not a change to the website, public WMI formula or production game files.",
        "",
        "The central result is modest: measured recent fouls predict slightly lower immediate foul probability, while the continuation component is slightly higher. A simple smooth-decay or makeup-call interpretation is not supported. Substitution after foul trouble and the decline in take-labeled fouls are much clearer than the proposed strategic or officiating mechanisms. Added live foul features do not improve the held-out win model. The coaching-optimality question remains causally unresolved.",
        "",
        "## Data and execution coverage",
        "",
        f"The source inventory contains **{audit['source_games']:,} games**, covering five full regular seasons and all 84 games of the 2025 playoffs. After quarantining {len(audit['quarantined_games'])} games with backward source clocks, the rich event study uses **{audit['games']:,} games and {audit['possessions']:,} possession groups**. The primary 2024–25 sample and all 84 playoff games are unaffected. H9 additionally uses stored 2019–20 and selected attendance-linked game WMI.",
        "",
        "| Season | Type | Source games | Retained games |",
        "|---|---|---:|---:|",
    ]
    for row in audit["coverage"]:
        lines.append(
            f"| {row['season']} | {row['type']} | {row['games']:,} | {row['retained_games']:,} |"
        )
    lines += [
        "",
        "The attachment is a research roadmap, not a preregistration. Specifications and fallback analyses were developed during this run. Formal and exploratory tests are distinguished below; the results should be independently replicated before publication.",
        "",
        "Clock quarantine: "
        + ", ".join(audit["quarantined_games"])
        + ". The source contains replay clock reversals, an end-game memo with an earlier clock, and one inconsistent shot-event ordering. These complete games were excluded from rich-event fits rather than silently repairing their clocks. The raw cached data and anomalies remain available in `quarantined_clock_events.csv`; legacy game-level H9 does not rely on this clock reconstruction.",
        "",
        "### Statistical conventions",
        "",
        "Odds ratios and rate ratios have a null of 1; additive differences and correlations have a null of 0. An interaction odds ratio is a **ratio of odds ratios**, not a subgroup's standalone foul probability. Main effects in interaction models apply at the reference history state L2=0. Estimates are not percentage points unless explicitly converted: 0.01 probability/share units = 1 percentage point.",
        "",
        f"Regression uncertainty is clustered by game; count models use heteroskedasticity-robust game-level errors. Before/after and prediction differences use 1,000 whole-game bootstrap draws; their p-values use a normal approximation to the bootstrap standard error. Crew stability resamples crew identities. Benjamini–Hochberg correction is applied jointly across the {int(results.p_value.notna().sum())} reported inferential tests, not separately until something becomes significant. The tables show raw p and final q. Pointwise 95% intervals are not multiplicity-adjusted. Rows without p/q are descriptive estimates, not declarations of a passed formal test. Correlated tests and exploratory specification choices limit the certainty implied by q-values.",
        "",
        "### Reconstruction and leakage safeguards",
        "",
        "The foul definition and global last-two/next-two formula are unchanged. This separate parser adds explicit period boundaries to ownership-based grouping, measures score before the group's first event, handles regulation/OT clocks without knowing future overtime, and reconstructs foul/bonus counts before the current event. It remains a public-feed ownership approximation, not independently video-validated live control. Dead-ball ownership tagging, special fouls and overturned-event revisions are residual sources of error.",
        "",
        f"The parser adds {audit['period_boundaries_added_vs_ownership_only']:,} boundaries across the study relative to ownership-only grouping. Therefore these research values need not match earlier mobile-feed/ownership-only outputs exactly. All game score totals reconcile internally. Of the matching local schedule rows, only {audit['known_project_scores_compared']:,} have known final scores; those all match. Missing schedule scores are not counted as validation successes. Home/away matches were checked separately.",
        "",
        "Live WMI at the start of possession i includes a historical row only after its future-two window has completed (row ≤i−3). The current outcome, future N_t, final-game WMI and future overtime duration never enter win prediction. Whole games remain in chronological training/validation/test partitions. These checks reduce identifiable leakage, but the use of finalized historical play-by-play cannot guarantee reconstruction of the exact feed visible live at the time.",
        "",
        "## Hypothesis-by-hypothesis results",
        "",
    ]
    for h in range(1, 19):
        question, method, interpretation, limits = sections[h]
        lines += [
            f"### H{h}. {TITLES[h]}",
            "",
            f"**Question:** {question}",
            "",
            f"**Executed analysis:** {method}",
            "",
            table(results[results.hypothesis.eq(f"H{h}")]),
            "",
            f"**Interpretation:** {interpretation}",
            "",
            f"**Limits and prior coverage:** {limits}",
            "",
        ]
        if h == 15:
            d = details["15"][-1]
            lines += [
                f"Matched sample: {d['matched_crew_year_pairs']} crew-year pairs, {d['distinct_repeated_crews']} distinct crews; no repeated pair meets a two-game-per-year minimum.",
                "",
            ]
        if h == 17:
            metrics = pd.read_csv(OUT / "H17_prediction_metrics.csv")
            lines += [
                "| Model | ROC-AUC | Average precision | Log loss | Brier | 10-bin ECE |",
                "|---|---:|---:|---:|---:|---:|",
            ]
            for r in metrics.itertuples():
                lines.append(
                    f"| {r.model} | {r.roc_auc:.6f} | {r.average_precision:.6f} | {r.log_loss:.6f} | {r.brier:.6f} | {r.ece_10_fixed_bins:.6f} |"
                )
            lines += [
                "",
                "ROC-AUC/average precision: higher is better. Log loss/Brier/ECE: lower is better. Average precision uses tie-aware scoring; ECE depends on binning and is secondary.",
                "",
            ]
    lines += [
        "## What has and has not been completed",
        "",
        "Completed: re-execution of the existing hypotheses, new empirical attempts for all previously unrun H1–H17 sections, supplemental H18, explicit sample sizes and effects, uncertainty and global multiple-test correction, new public-data joins, complete playoff coverage, a chronological win-prediction comparison, reproducible code and machine-readable outputs.",
        "",
        "Still not established: causality of referee behavior, call accuracy, the optimum keep/bench/return policy, a reliable restricted-attendance natural experiment, video-level attack/contest changes, transition-opportunity-adjusted causal rule impact, or precise stable crew rankings. These are identification/data limits, not analyses that were silently skipped. The ten separate advanced model architectures elsewhere in the attachment—such as Hawkes processes, transformers and offline reinforcement learning—are not all implemented by this hypothesis-focused run.",
        "",
        "## Reproduction and audit trail",
        "",
        "From the project root, run `OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python run_all_wmi_hypotheses.py`. The runner downloads commit-pinned public archives into an ignored cache, builds separate tables, executes the hypotheses and regenerates this report. `--fetch-only` and `--prepare-only` stop at those stages. `--report-only` rebuilds the report from already executed results. Run `pytest -q tests/test_all_wmi_hypotheses.py` for the new targeted guards.",
        "",
        "Files in this research folder: `all_hypothesis_results.csv` contains every reported estimate, interval, p and q; `analysis_details.json` contains formulas, sample details and prediction features; `run_audit.json` records automated coverage/scoring checks and hashes; `source_lock.json` and `source_manifest.json` pin the raw sources; `analysis_failures.json` lists failed analysis blocks. Section-specific CSVs retain model coefficients, matched events, crew pairs, component denominators and held-out predictions. The ignored `cache/` contains rich event and possession Parquet tables. Existing public datasets, earlier research outputs and unrelated working-tree changes were not overwritten by this runner.",
        "",
        f"Automated run audit: {'PASS' if all(audit['checks'].values()) else 'FAIL'}. Each check is independently listed in `run_audit.json`. The tests validate targeted invariants, not every basketball interpretation or causal assumption.",
        "",
        "## Sources and provenance",
        "",
        "1. [NBA-data public archive](https://github.com/shufinskiy/nba_data): rich NBA CDN event archives for regular seasons 2020–21 through 2024–25, 2025 playoffs, and the 2024–25 mobile archive for replay decisions. These are third-party archived copies of NBA feeds, not a claim of direct live NBA API verification. Exact commits, URLs, byte counts and SHA256 values are saved locally.",
        "",
        "2. [L2M research data archive](https://github.com/atlhawksfanatic/L2M): referee assignments and selected box/attendance data. Its close-game selection limits representativeness, and its assignment coverage stops before the final rounds of the 2025 playoffs.",
        "",
        "3. [NBA Rule 12 — Fouls and Penalties](https://official.nba.com/rule-no-12-fouls-and-penalties/): basis for regulation/OT team-foul quotas and late-period penalty reconstruction.",
        "",
        "4. [NBA transition-take-foul rule explanation](https://official.nba.com/video-transition-take-fouls/): policy context for the 2022–23 comparison; the archive's labels are an imperfect operational measure of the rule's targeted events.",
        "",
        "5. Existing local project game-search data: home/date fallback for 18 playoff games and stored WMI for H9. Its content hash is recorded in `run_audit.json`. The user's supplied roadmap defines the hypothesis questions, not the empirical findings.",
        "",
    ]
    (OUT / "full_hypothesis_report.md").write_text("\n".join(lines))
    # Report-only wording changes need not rerun the statistical fits. Preserve
    # their source hash while identifying the current report generator too.
    (OUT / "report_provenance.json").write_text(
        json.dumps(
            {
                "analysis_runner_sha256": audit["runner_sha256"],
                "report_generator_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "result_table_sha256": hashlib.sha256(
                    (OUT / "all_hypothesis_results.csv").read_bytes()
                ).hexdigest(),
                "note": "Report-only edits clarify wording and units; no fitted estimates are changed.",
            },
            indent=2,
        )
        + "\n"
    )


def fetch_inputs():
    CACHE.mkdir(parents=True, exist_ok=True)
    repos = ["shufinskiy/nba_data", "atlhawksfanatic/L2M"]
    lock_path = OUT / "source_lock.json"
    if lock_path.exists():
        locks = json.loads(lock_path.read_text())
    else:
        locks = {}
        for repo in repos:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/commits?per_page=1", timeout=30
            )
            response.raise_for_status()
            locks[repo] = response.json()[0]["sha"]
        lock_path.write_text(json.dumps(locks, indent=2) + "\n")
    names = [f"cdnnba_{year}" for year in range(2020, 2025)] + [
        "cdnnba_po_2024",
        "datanba_2024",
    ]
    sources = [
        (
            name + ".tar.xz",
            f"https://raw.githubusercontent.com/shufinskiy/nba_data/{locks[repos[0]]}/datasets/{name}.tar.xz",
        )
        for name in names
    ]
    sources += [
        (
            name,
            f"https://raw.githubusercontent.com/atlhawksfanatic/L2M/{locks[repos[1]]}/{path}",
        )
        for name, path in [
            ("box.csv", "0-data/stats_nba/stats_nba_box.csv"),
            ("attendance.csv", "0-data/bkref/bkref_box.csv"),
            ("assignments.csv", "0-data/official_nba/nba_referee_assignments.csv"),
        ]
    ]

    def download(source):
        name, url = source
        target = CACHE / name
        if not target.exists():
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        raw = target.read_bytes()
        entry = {
            "file": name,
            "url": url,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        print("input", name, len(raw), flush=True)
        return entry

    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(download, sources))
    (OUT / "source_manifest.json").write_text(json.dumps(entries, indent=2) + "\n")
    return entries


def read_archive(name, **kwargs):
    with tarfile.open(CACHE / f"{name}.tar.xz", "r:xz") as archive:
        member = archive.getmember(f"{name}.csv")
        return pd.read_csv(io.BytesIO(archive.extractfile(member).read()), **kwargs)


def gid(value):
    return str(int(value)).zfill(10)


def clock_seconds(value):
    match = re.fullmatch(r"PT(\d+)M([\d.]+)S", str(value))
    if not match:
        raise ValueError(f"Unrecognized clock {value}")
    return int(match[1]) * 60 + float(match[2])


def elapsed_seconds(period, remaining):
    return (
        (period - 1) * 720 + 720 - remaining
        if period <= 4
        else 2880 + (period - 5) * 300 + 300 - remaining
    )


def penalty_next_foul(period, remaining, total, last_two):
    return int(
        total >= (4 if period <= 4 else 3) or (remaining <= 120 and last_two >= 1)
    )


def sequence_columns(frame):
    out = frame.copy()
    foul = out.F_t.to_numpy(dtype=int)
    for j in range(1, 11):
        out[f"lag{j}"] = np.r_[
            np.zeros(min(j, len(out)), dtype=int), foul[: max(0, len(out) - j)]
        ]
    for k in (1, 2, 3, 5, 10):
        out[f"L{k}"] = out[[f"lag{j}" for j in range(1, k + 1)]].max(axis=1)
        out[f"N{k}"] = [int(foul[i + 1 : i + k + 1].any()) for i in range(len(foul))]
    out["L_t"] = out.L2
    out["N_t"] = out.N2
    out["M_t"] = out.F_t * (1 + out.N_t)
    # Current outcome is unknown at the start of this possession. A completed
    # WMI row i is usable only at start i+3, once its next-two window is known.
    n0 = n1 = m0 = m1 = 0
    live = []
    for i in range(len(out)):
        if i >= 3:
            j = i - 3
            if out.L2.iloc[j]:
                n1 += 1
                m1 += int(out.M_t.iloc[j])
            else:
                n0 += 1
                m0 += int(out.M_t.iloc[j])
        # Predeclared mild smoothing to avoid undefined early-game ratios.
        live.append(math.log(((m1 + 1) / (n1 + 2)) / ((m0 + 1) / (n0 + 2))))
    out["live_log_wmi"] = live
    out["recent_count"] = out[[f"lag{j}" for j in range(1, 6)]].sum(axis=1)
    return out


def parse_game(raw, year, postseason, metadata):
    """Ownership-group research parser with explicit period boundaries.

    This preserves the public foul exclusions and global windows. Additional
    period boundaries and correct OT clocks are audited against the legacy
    ownership-only grouping, rather than silently changing public WMI.
    """
    raw = (
        raw.sort_values(["orderNumber", "actionNumber"])
        .drop_duplicates("actionNumber")
        .copy()
    )
    game_id = gid(raw.gameId.iloc[0])
    team_map = {
        int(r.teamId): str(r.teamTricode)
        for r in raw.dropna(subset=["teamId", "teamTricode"]).itertuples()
    }
    if len(team_map) != 2:
        raise ValueError("Expected two teams")
    home_name = metadata.get("home_team_abbr")
    home_candidates = [t for t, name in team_map.items() if name == home_name]
    if not home_candidates:
        raise ValueError("No reliable home-team assignment")
    home = home_candidates[0]
    away = next(t for t in team_map if t != home)
    opponents = {home: away, away: home}
    raw["remaining"] = raw.clock.map(clock_seconds)
    raw["elapsed"] = [
        elapsed_seconds(int(p), c) for p, c in zip(raw.period, raw.remaining)
    ]
    raw["subType"] = raw.subType.fillna("").str.lower()
    raw["descriptor"] = raw.descriptor.fillna("").str.lower()
    raw["qualifiers"] = raw.qualifiers.fillna("").str.lower()
    raw["description"] = raw.description.fillna("")
    raw["home_before_event"] = pd.to_numeric(raw.scoreHome).shift(1, fill_value=0)
    raw["away_before_event"] = pd.to_numeric(raw.scoreAway).shift(1, fill_value=0)
    valid_owner = raw.possession.isin(team_map)
    valid = raw.loc[valid_owner]
    boundaries = valid.possession.ne(valid.possession.shift()) | valid.period.ne(
        valid.period.shift()
    )
    raw["group"] = (
        pd.Series(boundaries.cumsum().to_numpy(), index=valid.index)
        .reindex(raw.index)
        .ffill()
        .fillna(0)
        .astype(int)
    )
    legacy_boundaries = valid.possession.ne(valid.possession.shift())
    period_splits = int(boundaries.sum() - legacy_boundaries.sum())

    foul_counts = defaultdict(int)
    period_counts = defaultdict(int)
    late_counts = defaultdict(int)
    team_pf, bonus, player_pf, counted = [], [], [], []
    last_owner = None
    for r in raw.itertuples():
        before_count, before_bonus, after_count, is_counted = 0, 0, np.nan, 0
        if r.possession in team_map:
            last_owner = int(r.possession)
        offense = last_owner
        if offense is not None:
            defense = opponents[offense]
            key = (int(r.period), defense)
            before_count = period_counts[key]
            before_bonus = penalty_next_foul(
                int(r.period), r.remaining, period_counts[key], late_counts[key]
            )
        if r.actionType == "foul":
            personal = r.subType not in ("technical", "double technical")
            tid = int(r.teamId) if pd.notna(r.teamId) else 0
            pid = int(r.personId) if pd.notna(r.personId) else 0
            if personal and pid > 0:
                reported = r.foulPersonalTotal
                foul_counts[pid] = (
                    int(reported)
                    if pd.notna(reported) and reported > 0
                    else foul_counts[pid] + 1
                )
                after_count = foul_counts[pid]
            # Offensive and double personal fouls do not consume the team-foul quota.
            if (
                personal
                and r.subType != "offensive"
                and r.descriptor != "double"
                and tid in team_map
            ):
                period_counts[(int(r.period), tid)] += 1
                if r.remaining <= 120:
                    late_counts[(int(r.period), tid)] += 1
            if (
                offense is not None
                and r.possession in team_map
                and tid == opponents[offense]
                and r.subType not in ("offensive", "technical", "double technical")
            ):
                is_counted = 1
        team_pf.append(before_count)
        bonus.append(before_bonus)
        player_pf.append(after_count)
        counted.append(is_counted)
    raw["team_pf_before"] = team_pf
    raw["bonus_before"] = bonus
    raw["player_pf_after"] = player_pf
    raw["counted_def_foul"] = counted

    grouped = raw.loc[raw.group.gt(0)].copy()
    # The first valid ownership row anchors each group. Do not let admin rows
    # with ownership zero change which team's shot/FT is aggregated.
    owners = raw.loc[valid_owner].groupby("group").possession.first()
    grouped["owner"] = grouped.group.map(owners)
    own = grouped.teamId.eq(grouped.owner)
    shots = grouped.isFieldGoal.eq(1) & own
    grouped["fga"] = shots.astype(int)
    grouped["rim_attempts"] = (shots & grouped.shotDistance.le(4)).astype(int)
    grouped["three_attempts"] = (shots & grouped.actionType.eq("3pt")).astype(int)
    grouped["fta"] = (own & grouped.actionType.eq("freethrow")).astype(int)
    grouped["turnovers"] = (own & grouped.actionType.eq("turnover")).astype(int)
    counted_mask = grouped.counted_def_foul.eq(1)
    grouped["shooting_foul"] = (
        counted_mask & grouped.descriptor.eq("shooting")
    ).astype(int)
    grouped["take_fouls"] = (
        counted_mask & grouped.descriptor.str.contains("take")
    ).astype(int)
    grouped["transition_take"] = (
        counted_mask & grouped.descriptor.eq("transition take")
    ).astype(int)
    gb = grouped.groupby("group", sort=True)
    first = gb.first()
    last = gb.last()
    table = (
        gb[
            [
                "fga",
                "rim_attempts",
                "three_attempts",
                "fta",
                "turnovers",
                "take_fouls",
                "transition_take",
                "counted_def_foul",
            ]
        ]
        .sum()
        .rename(columns={"counted_def_foul": "foul_count"})
    )
    table["F_t"] = table.foul_count.gt(0).astype(int)
    table["shooting_foul"] = gb.shooting_foul.max()
    table["period"] = first.period.astype(int)
    table["period_bucket"] = table.period.clip(upper=5)
    table["offense"] = owners.map(team_map)
    table["defense"] = owners.map(opponents).map(team_map)
    table["home_offense"] = owners.eq(home).astype(int)
    table["bonus"] = first.bonus_before
    table["team_pf"] = first.team_pf_before
    table["end_elapsed"] = last.elapsed
    base = np.where(
        table.period.le(4), (table.period - 1) * 720, 2880 + (table.period - 5) * 300
    )
    table["start_elapsed"] = np.maximum(base, table.end_elapsed.shift(1, fill_value=0))
    table["remaining"] = np.where(table.period.le(4), 720, 300) - (
        table.start_elapsed - base
    )
    table["reg_remaining"] = (2880 - table.start_elapsed).clip(lower=0)
    table["home_margin"] = first.home_before_event - first.away_before_event
    table["home_margin_end"] = last.scoreHome - last.scoreAway
    table["score_diff"] = table.home_margin * (2 * table.home_offense - 1)
    table["margin"] = table.home_margin.abs()
    table["home_points"] = last.scoreHome - first.home_before_event
    table["away_points"] = last.scoreAway - first.away_before_event
    table["own_points"] = np.where(
        table.home_offense, table.home_points, table.away_points
    )
    table["net_points"] = (table.home_points - table.away_points) * (
        2 * table.home_offense - 1
    )
    table["source_group"] = table.index
    table["pos"] = np.arange(len(table))
    for key, value in {
        "game_id": game_id,
        "year": year,
        "postseason": postseason,
        "home": team_map[home],
        "away": team_map[away],
        "date": str(metadata["game_date"]),
    }.items():
        table[key] = value
    table = sequence_columns(table.reset_index(drop=True))
    table["late_strategy"] = (
        (table.period.ge(4))
        & (
            (table.remaining.le(35) & table.score_diff.gt(3))
            | (table.remaining.le(15) & table.score_diff.ge(1))
        )
    ).astype(int)
    # Group-preserving history sensitivity: remove suspected intentional calls
    # from the foul process without compressing the possession time axis.
    clean = sequence_columns(table.assign(F_t=table.F_t * (1 - table.late_strategy)))
    for c in ("F_t", "L_t", "N_t", "M_t"):
        table["clean_" + c] = clean[c]
    for stat in ("rim_attempts", "fga", "three_attempts", "fta"):
        table["prior_" + stat] = (
            table[stat].shift(1).rolling(5, min_periods=1).sum().fillna(0)
        )
    meta = {
        "game_id": game_id,
        "year": year,
        "postseason": postseason,
        "date": metadata["game_date"],
        "home": team_map[home],
        "away": team_map[away],
        "home_score": float(raw.scoreHome.iloc[-1]),
        "away_score": float(raw.scoreAway.iloc[-1]),
        "period_splits": period_splits,
        "raw_events": len(raw),
        "possessions": len(table),
        "crew": "|".join(
            sorted(str(metadata.get(f"official{i}", "")) for i in (1, 2, 3))
        ),
        "foul_drawn_ids": int(
            raw.loc[raw.counted_def_foul.eq(1), "foulDrawnPersonId"].notna().sum()
        ),
    }
    # Compact event table retained for player/event studies and exact audit.
    keep = [
        "actionNumber",
        "period",
        "remaining",
        "elapsed",
        "actionType",
        "subType",
        "descriptor",
        "qualifiers",
        "personId",
        "teamId",
        "teamTricode",
        "foulDrawnPersonId",
        "player_pf_after",
        "counted_def_foul",
        "shotDistance",
        "group",
        "description",
        "isFieldGoal",
    ]
    ev = raw[keep].copy()
    ev["game_id"] = game_id
    ev["year"] = year
    ev["postseason"] = postseason
    return table, ev, meta


def prepare_tables():
    assignments = pd.read_csv(CACHE / "assignments.csv", low_memory=False)
    assignments["game_id"] = assignments.game_id.map(gid)
    assignments["game_date"] = pd.to_datetime(
        assignments.game_date, format="%m/%d/%Y"
    ).dt.strftime("%Y-%m-%d")
    metadata = (
        assignments.drop_duplicates("game_id").set_index("game_id").to_dict("index")
    )
    search = pd.read_csv(
        ROOT / "wmi_search_games_2019_2026.csv", dtype={"game_id": str}
    )
    # The assignment archive stops before the 2025 conference finals. The
    # existing project schedule supplies home/date, never invented officials.
    for r in search.itertuples():
        if r.game_id not in metadata:
            metadata[r.game_id] = {
                "home_team_abbr": r.home_team,
                "game_date": str(r.game_date_et)[:10],
                "official1": np.nan,
                "official2": np.nan,
                "official3": np.nan,
            }
    datasets = [(f"cdnnba_{y}", y, 0) for y in range(2020, 2025)] + [
        ("cdnnba_po_2024", 2024, 1)
    ]
    for name, year, post in datasets:
        prefix = CACHE / name
        expected = set(
            search.loc[
                search.season_start_year.eq(year)
                & search.season_type.eq("Playoffs" if post else "Regular Season"),
                "game_id",
            ]
        )
        summary_path = OUT / f"{name}_games.csv"
        if prefix.with_suffix(".poss.parquet").exists() and summary_path.exists():
            cached_ids = set(pd.read_csv(summary_path, dtype={"game_id": str}).game_id)
            if expected.issubset(cached_ids):
                continue
        raw = read_archive(name, low_memory=False)
        tables, events, summaries, failures = [], [], [], []
        for i, (game_id, group) in enumerate(raw.groupby("gameId", sort=False)):
            game_id = gid(game_id)
            # Archive labels may include Cup final/play-in. Explicit prefix filter.
            if not game_id.startswith("004" if post else "002"):
                continue
            try:
                table, ev, meta = parse_game(
                    group, year, post, metadata.get(game_id, {})
                )
                if table.F_t.sum() == 0 or meta["home_score"] == meta["away_score"]:
                    raise ValueError("No fouls or tied/incomplete final")
                tables.append(table)
                events.append(ev)
                summaries.append(meta)
            except Exception as exc:
                failures.append(
                    {"dataset": name, "game_id": game_id, "error": str(exc)}
                )
            if (i + 1) % 100 == 0:
                print("parsed", name, i + 1, "failures", len(failures), flush=True)
        pd.concat(tables, ignore_index=True).to_parquet(
            prefix.with_suffix(".poss.parquet"), index=False
        )
        pd.concat(events, ignore_index=True).to_parquet(
            prefix.with_suffix(".events.parquet"), index=False
        )
        pd.DataFrame(summaries).to_csv(OUT / f"{name}_games.csv", index=False)
        (OUT / f"{name}_failures.json").write_text(
            json.dumps(failures, indent=2) + "\n"
        )
        print("dataset complete", name, len(tables), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only:
        build_report()
        return
    fetch_inputs()
    if not args.fetch_only:
        prepare_tables()
        print("Table preparation complete", datetime.now(UTC).isoformat())
        if not args.prepare_only:
            run_study()


if __name__ == "__main__":
    main()
