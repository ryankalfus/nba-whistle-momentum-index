"""Audit-gated matched models; the CLI executes only internally synthetic fits."""

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import platform
import warnings

import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from whistle_research import audit
from whistle_research.sources import file_digest, safe_path

NUMERIC = ("period", "clock", "score_margin", "home_defense", "defense_counted_fouls")
STRONG_NUMERIC = ("score_difference",)
CATEGORICAL = ("defense_team_id", "offense_team_id", "start_type")
HISTORY = ("previous_foul_1", "previous_foul_2")
MODEL_NAMES = ("base_rate", "additive_context", "nonlinear_context", "nonlinear_history")
C_GRID = (0.1, 1.0, 10.0)
MAX_ITER = 2000
UNKNOWN = "__UNKNOWN__"


class BlockedError(ValueError):
    """Scientific prerequisites are absent; contains a machine-readable report."""

    def __init__(self, reasons):
        self.report = {"status": "BLOCKED", "reasons": sorted(set(reasons)),
                       "next_step": "Supply passing bound audit evidence, verified sources, eligible rows and a frozen unseen-cohort protocol."}
        super().__init__("; ".join(self.report["reasons"]))


def row_digest(rows):
    """Canonical hash binds every input field and supplied row order."""
    return audit.digest(rows)


def specification():
    """Freeze this configuration and both source hashes before evaluation."""
    return {"schema": "matched-model-v1", "numeric": list(NUMERIC), "strong_numeric": list(STRONG_NUMERIC), "categorical": list(CATEGORICAL),
            "history": list(HISTORY), "models": list(MODEL_NAMES), "C_grid": list(C_GRID),
            "max_iter": MAX_ITER, "solver": "lbfgs", "penalty": "l2",
            "missing": "numeric constant zero plus fixed missing indicators; categorical unknown sentinel",
            "nonlinear": "clock/720 squared; margin/30 squared; margin/30 times clock/720; home times margin/30",
            "selection": "tune possession logloss; first grid value breaks ties; no train+tune refit",
            "primary": "history_minus_context_possession_logloss", "bootstrap_resamples": 999,
            "bootstrap_seed": 137, "confidence": 0.95, "probability_clip": 1e-15,
            "sources": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ("modeling.py", "evaluation.py", "release.py")}}


def validate_rows(rows):
    """No outcome filtering; reject ambiguous metadata/order and unknown targets."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("a nonempty list of possession rows is required")
    metadata, previous, seen = {}, {}, set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("row must be a mapping")
        game = row.get("game_id")
        if not audit.text(game):
            raise ValueError("nonempty game_id required")
        day = date.fromisoformat(row["date"])
        if day.isoformat() != row["date"]:
            raise ValueError("date must use YYYY-MM-DD")
        if not all(audit.text(row.get(k)) for k in ("season", "game_type")):
            raise ValueError("season and game_type required")
        meta = (day, row["season"], row["game_type"])
        if game in metadata and metadata[game] != meta:
            raise ValueError("inconsistent game date/season/type")
        metadata[game] = meta
        number = row.get("possession_number")
        if type(number) is not int or number < 1 or (game, number) in seen:
            raise ValueError("unique positive possession number required")
        if number <= previous.get(game, 0):
            raise ValueError("within-game order must increase")
        seen.add((game, number))
        previous[game] = number
        if type(row.get("outcome")) is not int or row["outcome"] not in (0, 1):
            raise ValueError("known binary integer outcome required for every row")
        for key in (*NUMERIC, *STRONG_NUMERIC, *HISTORY):
            value = row.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not np.isfinite(value)):
                raise ValueError(f"invalid numeric context: {key}")
            if key in (*HISTORY, "home_defense") and value not in (None, 0, 1):
                raise ValueError(f"invalid binary context: {key}")
            if key in ("clock", "score_margin", "defense_counted_fouls") and value is not None and value < 0:
                raise ValueError(f"negative context: {key}")
        period, clock = row.get("period"), row.get("clock")
        if period is not None and (period < 1 or int(period) != period):
            raise ValueError("invalid period")
        if clock is not None and clock > (300 if period is not None and period > 4 else 720):
            raise ValueError("clock exceeds period length")
        for key in CATEGORICAL:
            if row.get(key) is not None and not isinstance(row[key], (str, int)):
                raise ValueError(f"invalid categorical context: {key}")
    return metadata


def chronological_split(rows, split):
    """Date boundaries assign entire games; same-day games cannot cross splits."""
    metadata = validate_rows(rows)
    keys = ("train_start", "tune_start", "test_start", "test_end")
    boundaries = [date.fromisoformat(split[k]) for k in keys]
    if not all(a < b for a, b in zip(boundaries, boundaries[1:])):
        raise ValueError("strictly increasing chronological split dates required")
    a, b, c, d = boundaries
    result = {"train": [], "tune": [], "test": []}
    for row in rows:
        day = metadata[row["game_id"]][0]
        if not a <= day < d:
            raise ValueError("row outside frozen split range")
        label = "train" if day < b else "tune" if day < c else "test"
        result[label].append(row)
    if any(not subset for subset in result.values()):
        raise ValueError("each chronological split requires at least one whole game")
    return result


def require_evidence(rows, evidence):
    """Fail closed on audit/protocol/parser/frame/row/source eligibility bindings.

    Hashes and timestamps bind supplied attestations, not their external truth.
    Source bytes are rehashed under source_root only after the audit gate passes.
    """
    reasons = []
    if not isinstance(evidence, dict):
        raise BlockedError(["audit_and_frozen_protocol_evidence_required"])
    gate = audit.check_gate(evidence.get("plan"), evidence.get("reviews"), evidence.get("config"))
    if gate.get("status") != "PASS_CONDITIONAL":
        raise BlockedError(["independent_audit_not_passed", *gate.get("reasons", [])])
    try:
        plan, protocol, dataset = (evidence[k] for k in ("plan", "protocol", "dataset"))
        from whistle_research import features
        for key, expected in (("feature_version", features.FEATURE_VERSION),
                              ("feature_sha256", features.feature_module_sha256())):
            if protocol.get(key) != expected or dataset.get(key) != expected:
                reasons.append(f"dataset_protocol_{key}_mismatch")
        metadata = validate_rows(rows)
        if protocol.get("protocol_sha256") != audit.digest({k: v for k, v in protocol.items() if k != "protocol_sha256"}):
            reasons.append("frozen_protocol_hash_mismatch")
        if (protocol.get("frozen") is not True or not audit.text(protocol.get("freeze_id"))
                or protocol.get("evaluation_exposure") != "unseen_at_freeze"
                or not all(audit.text(protocol.get(k)) for k in ("exposure_inventory_ref", "unused_cohort_evidence_ref"))):
            reasons.append("frozen_unseen_evaluation_protocol_required")
        frozen = audit.timestamp(protocol.get("frozen_at"))
        opened = audit.timestamp(evidence.get("evaluation_started_at"))
        if opened <= frozen:
            reasons.append("evaluation_must_follow_protocol_freeze")
        if protocol.get("specification_sha256") != audit.digest(specification()):
            reasons.append("model_evaluation_specification_not_frozen")
        for key in ("parser_version", "parser_sha256", "plan_sha256", "frame_sha256"):
            if protocol.get(key) != plan.get(key) or dataset.get(key) != plan.get(key):
                reasons.append(f"dataset_protocol_{key}_mismatch")
        if dataset.get("rows_sha256") != row_digest(rows) or protocol.get("rows_sha256") != row_digest(rows):
            reasons.append("frozen_rows_hash_mismatch")
        threshold = protocol.get("meaningful_gain")
        if isinstance(threshold, bool) or not isinstance(threshold, (float, int)) or not np.isfinite(threshold) or threshold <= 0:
            reasons.append("positive_frozen_meaningful_gain_required")
        frame = {game["game_id"]: game for game in plan["frame"]}
        entries = dataset["games"]
        games = {game["game_id"]: game for game in entries}
        if len(games) != len(entries) or set(games) != {r["game_id"] for r in rows}:
            reasons.append("dataset_game_binding_mismatch")
        checked_sources = {}
        for game_id, game in games.items():
            source = frame[game_id]
            if (game.get("eligible") is not True or game.get("complete") is not True
                    or game.get("critical_unresolved") is not False
                    or game.get("source_sha256") != source["source_sha256"]
                    or (metadata[game_id][1], metadata[game_id][2]) != (source["season"], source["game_type"])):
                reasons.append("unknown_eligibility_or_source_binding")
            name = source["source_file"]
            if name not in checked_sources:
                checked_sources[name] = file_digest(safe_path(Path(evidence["source_root"]), name))[1]
            if checked_sources[name] != source["source_sha256"]:
                reasons.append("source_bytes_changed")
        chronological_split(rows, protocol["split"])
        from whistle_research import release
        release.validate_promoted_dataset(dataset, plan=plan, reviews=evidence["reviews"], config=evidence["config"])
    except BlockedError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OSError, OverflowError, ImportError):
        reasons.append("malformed_or_incomplete_bound_evidence")
    if reasons:
        raise BlockedError(reasons)
    return {"gate": gate, "protocol": protocol}


def _design(rows, *, nonlinear, history):
    """Fixed deterministic allowlist. No fitting, outcome access or future rows."""
    numeric_names = list(NUMERIC)
    if nonlinear:
        numeric_names += [*STRONG_NUMERIC, "clock_squared", "margin_squared", "margin_clock", "home_margin"]
    if history:
        numeric_names += list(HISTORY)
    matrix = []
    for row in rows:
        numeric = [row.get(k) if row.get(k) is not None else np.nan for k in NUMERIC]
        if nonlinear:
            clock, margin, home = numeric[1] / 720, numeric[2] / 30, numeric[3]
            numeric += [row.get(k) if row.get(k) is not None else np.nan for k in STRONG_NUMERIC]
            numeric += [clock**2, margin**2, margin * clock, home * margin]
        if history:
            numeric += [row.get(k) if row.get(k) is not None else np.nan for k in HISTORY]
        # Missing indicators are always present, even when training has no missing values.
        missing = [float(np.isnan(v)) for v in numeric]
        categories = [UNKNOWN if row.get(k) is None else f"value:{row[k]}" for k in CATEGORICAL]
        matrix.append([*numeric, *missing, *categories])
    return np.array(matrix, dtype=object), numeric_names


def _pipeline(numeric_count, c):
    numeric = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True)),
                        ("scale", StandardScaler())])
    transform = ColumnTransformer([
        ("numeric", numeric, list(range(numeric_count * 2))),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         list(range(numeric_count * 2, numeric_count * 2 + len(CATEGORICAL))))])
    return Pipeline([("transform", transform),
                     ("model", LogisticRegression(C=c, solver="lbfgs", max_iter=MAX_ITER, random_state=0))])


def _fit(rows, split):
    from whistle_research.evaluation import log_losses

    subsets = chronological_split(rows, split)
    y_train = np.array([r["outcome"] for r in subsets["train"]])
    if len(np.unique(y_train)) != 2:
        raise ValueError("single-class training data; matched logistic comparison withheld")
    y_tune = np.array([r["outcome"] for r in subsets["tune"]])
    base = float(y_train.mean())
    prediction_packet = {"row_ids": [[r["game_id"], r["possession_number"]] for r in subsets["test"]],
                         "probabilities": {"base_rate": [base] * len(subsets["test"])}}
    diagnostics = {"base_rate": {"training_rate": base, "tuning_candidates": 0}}
    pipelines = {}
    for name in MODEL_NAMES[1:]:
        nonlinear, history = name != "additive_context", name == "nonlinear_history"
        train, names = _design(subsets["train"], nonlinear=nonlinear, history=history)
        tune, _ = _design(subsets["tune"], nonlinear=nonlinear, history=history)
        test, _ = _design(subsets["test"], nonlinear=nonlinear, history=history)
        candidates = []
        for c in C_GRID:
            pipe = _pipeline(len(names), c)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                pipe.fit(train, y_train)
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                raise ValueError(f"nonconvergence in {name} C={c}; comparison withheld")
            score = float(log_losses(y_tune, pipe.predict_proba(tune)[:, 1]).mean())
            candidates.append((score, c, pipe))
        best_score, c, selected = min(candidates, key=lambda item: (item[0], C_GRID.index(item[1])))
        pipelines[name] = selected
        prediction_packet["probabilities"][name] = selected.predict_proba(test)[:, 1].tolist()
        diagnostics[name] = {"selected_C": c, "tune_logloss": best_score,
                             "tuning_candidates": len(C_GRID), "training_rows": len(train),
                             "iterations": int(selected.named_steps["model"].n_iter_.max()),
                             "numeric_features": names,
                             "candidate_scores": [{"C": c, "tune_logloss": s} for s, c, _ in candidates]}
    return {"subsets": subsets, "predictions": prediction_packet, "diagnostics": diagnostics,
            "pipelines": pipelines}


def _fitted_pipeline_digest(pipe):
    transform = pipe.named_steps["transform"]
    numeric = transform.named_transformers_["numeric"]
    model = pipe.named_steps["model"]
    return audit.digest({"coefficients": model.coef_.tolist(), "intercept": model.intercept_.tolist(),
                         "classes": model.classes_.tolist(),
                         "imputer_statistics": numeric.named_steps["impute"].statistics_.tolist(),
                         "scaler_mean": numeric.named_steps["scale"].mean_.tolist(),
                         "scaler_scale": numeric.named_steps["scale"].scale_.tolist(),
                         "categories": [values.tolist() for values in transform.named_transformers_["categorical"].categories_]})


def fit_real(rows, *, evidence):
    """Fit and internally score supplied rows only after all scientific gates."""
    checked = require_evidence(rows, evidence)
    protocol = checked["protocol"]
    fitted = _fit(rows, protocol["split"])
    from whistle_research.evaluation import _evaluate
    evaluation = _evaluate(fitted["subsets"]["test"], fitted["predictions"],
                           meaningful_gain=protocol["meaningful_gain"])
    spec = specification()
    test_features = [
        {key: row.get(key) for key in ("game_id", "possession_number", *NUMERIC, *STRONG_NUMERIC, *CATEGORICAL, *HISTORY)}
        for row in fitted["subsets"]["test"]
    ]
    provenance = {
        "protocol_sha256": protocol["protocol_sha256"], "rows_sha256": row_digest(rows),
        "partition_rows_sha256": {label: row_digest(subset) for label, subset in fitted["subsets"].items()},
        "test_features_sha256": audit.digest(test_features), "specification_sha256": audit.digest(spec),
        "implementation_sha256": spec["sources"],
        "promoted_dataset_sha256": audit.digest(evidence["dataset"]),
        "provisional_manifest_sha256": evidence["dataset"]["provisional_manifest_sha256"],
        "rows_file_sha256": evidence["dataset"]["rows_file_sha256"],
        "row_provenance_file_sha256": evidence["dataset"]["row_provenance_sha256"],
        "parser_version": protocol["parser_version"], "parser_sha256": protocol["parser_sha256"],
        "feature_version": protocol["feature_version"], "feature_sha256": protocol["feature_sha256"],
        "source_sha256_by_game": {game["game_id"]: game["source_sha256"] for game in evidence["dataset"]["games"]},
        "audit_plan_sha256": checked["gate"]["plan_sha256"],
        "audit_reviews_sha256": checked["gate"]["reviews_sha256"],
        "audit_config_sha256": checked["gate"]["config_sha256"],
        "fitted_pipeline_sha256": {name: _fitted_pipeline_digest(pipe) for name, pipe in fitted["pipelines"].items()},
        "base_rate": fitted["diagnostics"]["base_rate"]["training_rate"],
    }
    evaluation["provenance"] = provenance
    return {"status": "GATED_EXPLORATORY_RESULT_NOT_PUBLICATION_APPROVAL",
            "diagnostics": fitted["diagnostics"], "predictions": fitted["predictions"],
            "evaluation": evaluation, "provenance": provenance,
            "protocol_sha256": protocol["protocol_sha256"]}


def _synthetic_rows(seed, games=90, possessions=36):
    rng = np.random.default_rng(seed)
    rows = []
    for game in range(games):
        past = [0, 0]
        for number in range(1, possessions + 1):
            margin = float(rng.integers(0, 25))
            clock = float(720 - (number % 9) * 75)
            home = number % 2
            eta = -2.2 + 0.03 * margin + 0.7 * past[-1] + 0.3 * past[-2] + 0.2 * home
            outcome = int(rng.random() < 1 / (1 + np.exp(-eta)))
            rows.append({"game_id": f"synthetic-{game:03d}",
                         "date": (date(2030, 1, 1) + timedelta(days=game)).isoformat(),
                         "season": "synthetic-2030", "game_type": "playoffs" if game % 7 == 0 else "regular_season",
                         "possession_number": number, "period": 1 + (number - 1) // 9,
                         "clock": clock, "score_margin": margin,
                         "score_difference": margin if (game + number) % 3 else -margin,
                         "home_defense": home,
                         "defense_counted_fouls": min(sum(past), 5),
                         "defense_team_id": str((game + home) % 6), "offense_team_id": str((game + 1 - home) % 6),
                         "previous_foul_1": past[-1], "previous_foul_2": past[-2],
                         "start_type": "synthetic_transfer", "outcome": outcome})
            past.append(outcome)
    return rows


def synthetic_demo(seed=20261102):
    from whistle_research.evaluation import _evaluate

    rows = _synthetic_rows(seed)
    split = {"train_start": "2030-01-01", "tune_start": "2030-02-24",
             "test_start": "2030-03-14", "test_end": "2030-04-01"}
    fitted = _fit(rows, split)
    return {"schema": "synthetic-model-demo-v1", "seed": seed,
            "status": "SYNTHETIC_ONLY_NO_SCIENTIFIC_ACCEPTANCE", "python": platform.python_version(),
            "parser": "none; internally generated possession rows", "numpy": np.__version__,
            "sklearn": sklearn.__version__, "specification": specification(), "rows_sha256": row_digest(rows),
            "split": split, "split_games": {k: sorted({r["game_id"] for r in v}) for k, v in fitted["subsets"].items()},
            "diagnostics": fitted["diagnostics"],
            "evaluation": _evaluate(fitted["subsets"]["test"], fitted["predictions"])}


def _strict_json(text):
    def constant(value):
        raise ValueError(f"nonfinite JSON number: {value}")

    def number(value):
        parsed = float(value)
        if not np.isfinite(parsed):
            raise ValueError("JSON number exceeds finite range")
        return parsed

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result

    return json.loads(text, parse_constant=constant, parse_float=number,
                      object_pairs_hook=unique_object)


def _read_rows(path):
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            rows = [_strict_json(line) for line in stream if line.strip()]
    else:
        rows = _strict_json(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a nonempty JSON array or JSONL file of objects")
    return rows


def _emit_result(result, output):
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if output is None:
        print(serialized, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(serialized)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("synthetic", "real"), nargs="?", default="synthetic")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--rows", type=Path, help="real mode: JSONL or JSON array of possession rows")
    parser.add_argument("--evidence", type=Path, help="real mode: bound audit/dataset/frozen-protocol JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "synthetic":
        if args.rows is not None or args.evidence is not None:
            parser.error("--rows and --evidence require real mode; synthetic data are generated internally")
        if args.output is not None and args.output.exists():
            parser.error("output file already exists; choose a new file")
        _emit_result(synthetic_demo(args.seed), args.output)
        return 0
    if args.output is not None and args.output.exists():
        _emit_result(BlockedError(["output_already_exists_choose_a_new_file"]).report, None)
        return 1
    try:
        if args.rows is None or args.evidence is None:
            raise BlockedError(["real_mode_requires_rows_and_bound_evidence_files"])
        evidence = _strict_json(args.evidence.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be one JSON object")
        # Fail before loading potentially large or protected target exports.
        gate = audit.check_gate(evidence.get("plan"), evidence.get("reviews"), evidence.get("config"))
        if gate.get("status") != "PASS_CONDITIONAL":
            raise BlockedError(["independent_audit_not_passed", *gate.get("reasons", [])])
        rows = _read_rows(args.rows)
        result = fit_real(rows, evidence=evidence)
    except BlockedError as error:
        result = error.report
    except (OSError, ValueError, TypeError, KeyError) as error:
        result = BlockedError([f"real_input_or_model_error: {error}"]).report
        result["next_step"] = "Correct the supplied row/evidence files; all audit and frozen-protocol gates remain required."
    try:
        _emit_result(result, args.output)
    except (OSError, ValueError, TypeError) as error:
        _emit_result(BlockedError([f"output_write_failed: {error}"]).report, None)
        return 1
    return 1 if result.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
