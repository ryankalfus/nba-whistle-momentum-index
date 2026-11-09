"""The notebook must display the exact synthetic artifacts bound by its report."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest

from scripts.export_v2_site import BUNDLE_DOCUMENTS, bundled_markdown, export


def write_json(path, value):
    path.write_text(json.dumps(value) + "\n")
    raw = path.read_bytes()
    return {"path": path.name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


@pytest.fixture
def run_files(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    math = run / "math.json"
    models = run / "models.json"
    report = run / "report.json"
    artifacts = {
        "math": write_json(math, {"schema_version": "synthetic-mathematics-v1"}),
        "models": write_json(models, {"schema": "synthetic-model-demo-v1", "evaluation": {
            "paired_logloss": {"estimate": -0.002}, "row_ids": [["synthetic", 1]]}}),
    }
    write_json(report, {"schema_version": "development-research-report-v1", "artifacts": artifacts})
    return report, math, models, tmp_path / "export"


def test_export_verifies_report_roles_before_compacting(run_files):
    report, math, models, output = run_files
    result = json.loads(export(report, math, models, output).read_text())
    assert "row_ids" not in result["models"]["evaluation"]
    assert result["models"]["evaluation"]["paired_logloss"]["estimate"] == -0.002
    assert [item["role"] for item in result["input_files"]] == ["report", "math", "models"]
    for item in result["input_files"][1:]:
        assert item["report_binding"] == f"{item['role']}.json"


@pytest.mark.parametrize("role", ["math", "models"])
def test_modified_supplied_copy_is_rejected(run_files, role):
    report, math, models, output = run_files
    original = math if role == "math" else models
    supplied = output.parent / f"changed-{role}.json"
    data = json.loads(original.read_text())
    if role == "models":
        data["evaluation"]["paired_logloss"]["estimate"] = -999
    else:
        data["tampered_result"] = -999
    write_json(supplied, data)
    with pytest.raises(ValueError, match="does not match report binding"):
        export(report, supplied if role == "math" else math,
               supplied if role == "models" else models, output)
    assert not output.exists()


def test_modified_bound_file_is_rejected_even_with_original_supplied_copy(run_files):
    report, math, models, output = run_files
    supplied = output.parent / "original-models.json"
    supplied.write_bytes(models.read_bytes())
    data = json.loads(models.read_text())
    data["evaluation"]["paired_logloss"]["estimate"] = -999
    write_json(models, data)
    with pytest.raises(ValueError, match="bound artifact does not match"):
        export(report, math, supplied, output)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["missing", "wrong_hash", "wrong_bytes", "absolute_path", "swapped_roles", "bool_bytes"])
def test_invalid_role_catalog_fails_closed(run_files, mutation):
    report, math, models, output = run_files
    data = json.loads(report.read_text())
    artifacts = deepcopy(data["artifacts"])
    if mutation == "missing":
        artifacts.pop("models")
    elif mutation == "wrong_hash":
        artifacts["models"]["sha256"] = "0" * 64
    elif mutation == "wrong_bytes":
        artifacts["models"]["bytes"] += 1
    elif mutation == "absolute_path":
        artifacts["models"]["path"] = str(models.resolve())
    elif mutation == "bool_bytes":
        artifacts["models"]["bytes"] = True
    else:
        artifacts["math"], artifacts["models"] = artifacts["models"], artifacts["math"]
    data["artifacts"] = artifacts
    write_json(report, data)
    with pytest.raises(ValueError):
        export(report, math, models, output)
    assert not output.exists()


def test_identical_copy_is_accepted_and_hashes_remain_raw(run_files):
    report, math, models, output = run_files
    supplied = output.parent / "copied-models.json"
    supplied.write_bytes(models.read_bytes())
    result = json.loads(export(report, math, supplied, output).read_text())
    evidence = next(item for item in result["input_files"] if item["role"] == "models")
    assert evidence["sha256"] == sha256(models.read_bytes()).hexdigest()
    assert evidence["bytes"] == len(models.read_bytes())
    assert "row_ids" not in result["models"]["evaluation"]


@pytest.fixture
def exploratory_files(run_files):
    report, math, models, output = run_files
    run = report.parent / 'exploratory'
    run.mkdir()
    flags = dict(eligible=False, scientific_approval=False, publication_authorized=False,
                 evaluation_exposure='retrospective_previously_exposed', analysis_id='fixture')
    plan = {'schema_version': 'provisional-exploratory-plan-v1', **flags}
    cohort = {'schema_version': 'provisional-exploratory-cohort-v1', **flags,
              'status': 'PROVISIONAL_NOT_INDEPENDENTLY_VALIDATED',
              'counts': {}, 'partitions': {}, 'games': [{'game_id': 'fixture'}]}
    artifacts = {'plan': write_json(run / 'plan.json', plan),
                 'cohort': write_json(run / 'cohort.json', cohort)}
    result = {'schema_version': 'provisional-exploratory-result-v1', **flags,
              'status': 'EXPLORATORY_ONLY_NOT_VALIDATED',
              'plan_sha256': artifacts['plan']['sha256'],
              'evaluation': {'models': {name: {'possession_logloss': .5, 'brier': .2}
                                       for name in ('base_rate', 'additive_context',
                                                    'nonlinear_context', 'nonlinear_history')},
                             'paired_logloss': {'estimate': -.01, 'interval': [-.02, .01],
                                                'conditions_on_fitted_models': True},
                             'decision': {'classification': 'NOT_SPECIFIED'}, 'row_ids': [1]}}
    artifacts['model_result'] = write_json(run / 'result.json', result)
    for role in ('selected_rows', 'predictions'):
        artifacts[role] = write_json(run / f'{role}.jsonl', {'fixture': True})
    empirical = run / 'report.json'
    write_json(empirical, {'schema_version': 'exploratory-research-report-v1', **flags,
                          'status': 'EXPLORATORY_ONLY_NOT_VALIDATED',
                          'plan_sha256': artifacts['plan']['sha256'], 'cohort': cohort,
                          'artifacts': artifacts})
    return empirical


def test_exploratory_bundle_preserves_gate_receipts_and_compacts(run_files, exploratory_files):
    report, math, models, output = run_files
    data = json.loads(export(report, math, models, output, exploratory=exploratory_files,
                             bundle=True).read_text())
    assert 'games' not in data['exploratory']['cohort']
    assert 'games' not in data['exploratory']['report']['cohort']
    assert 'row_ids' not in data['exploratory']['result']['evaluation']
    assert data['report'] == json.loads(report.read_text())
    assert len(data['input_files']) == 9
    assert data['exploratory']['report']['eligible'] is False
    for name in ('app.js', 'styles.css'):
        assert (output / name).read_bytes() == (Path(__file__).parents[2] / 'v2' / name).read_bytes()


@pytest.mark.parametrize('mutation', ['hash', 'bytes', 'roles', 'absolute', 'traversal', 'symlink',
                                     'swapped_roles', 'report_schema', 'result_schema', 'plan_schema', 'cohort_schema',
                                     'report_flag', 'result_flag', 'plan_flag', 'cohort_flag',
                                     'analysis', 'plan_hash', 'cohort_mismatch', 'infinity',
                                     'missing_loss', 'classification'])
def test_exploratory_rejects_invalid_bound_evidence(run_files, exploratory_files, mutation):
    report, math, models, output = run_files
    data = json.loads(exploratory_files.read_text())
    if mutation in {'hash', 'bytes', 'absolute', 'traversal', 'symlink'}:
        binding = data['artifacts']['predictions']
        if mutation == 'hash':
            binding['sha256'] = '0' * 64
        elif mutation == 'bytes':
            binding['bytes'] = True
        elif mutation == 'absolute':
            binding['path'] = str((exploratory_files.parent / binding['path']).resolve())
        elif mutation == 'traversal':
            binding['path'] = '../' + binding['path']
        else:
            outside = exploratory_files.parent.parent / 'outside.json'
            outside.write_text('{}')
            link = exploratory_files.parent / 'escape.json'
            link.symlink_to(outside)
            binding['path'] = link.name
    elif mutation == 'roles':
        data['artifacts']['models'] = data['artifacts'].pop('model_result')
    elif mutation == 'swapped_roles':
        data['artifacts']['cohort'], data['artifacts']['model_result'] = (
            data['artifacts']['model_result'], data['artifacts']['cohort'])
    elif mutation == 'report_schema':
        data['schema_version'] = 'unknown'
    elif mutation == 'report_flag':
        data['eligible'] = True
    elif mutation == 'cohort_mismatch':
        data['cohort']['counts']['fake'] = 99
    else:
        role = 'plan' if mutation.startswith('plan_') else 'cohort' if mutation.startswith('cohort_') else 'model_result'
        path = exploratory_files.parent / data['artifacts'][role]['path']
        value = json.loads(path.read_text())
        if mutation.endswith('_schema'):
            value['schema_version'] = 'unknown'
        elif mutation.endswith('_flag'):
            value['scientific_approval'] = True
        elif mutation == 'analysis':
            value['analysis_id'] = 'different'
        elif mutation == 'plan_hash':
            value['analysis_id'] = 'different-plan'
        elif mutation == 'classification':
            value['evaluation']['decision']['classification'] = 'USEFUL'
        elif mutation == 'missing_loss':
            value['evaluation']['models']['base_rate']['brier'] = None
        else:
            value['evaluation']['models']['base_rate']['brier'] = float('inf')
        data['artifacts'][role] = write_json(path, value)
    write_json(exploratory_files, data)
    with pytest.raises(ValueError):
        export(report, math, models, output, exploratory=exploratory_files)
    assert not output.exists()


def test_bundle_links_resolve_inside_bundle_without_changing_sources(run_files, exploratory_files):
    report, math, models, output = run_files
    root = Path(__file__).parents[2]
    original = (root / 'v2' / 'index.html').read_bytes()
    originals = {name: (root / name).read_bytes() for name in BUNDLE_DOCUMENTS}
    export(report, math, models, output, exploratory=exploratory_files, bundle=True)
    html = (output / 'index.html').read_text()
    assert 'Back to question' in html
    assert 'href="docs/EXPLORATORY_ANALYSIS.md"' in html
    assert (root / 'v2' / 'index.html').read_bytes() == original
    for value in re.findall(r'(?:href|src)="([^"]+)"', html):
        if value.startswith('#'):
            continue
        destination = (output / value).resolve()
        assert destination.is_relative_to(output.resolve())
        assert destination.is_file()
    for name, raw in originals.items():
        assert (root / name).read_bytes() == raw
        destination = output / name
        if destination.suffix == '.json':
            assert destination.read_bytes() == raw
            continue
        text = destination.read_text()
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', text):
            if target.startswith(('https://', 'http://', '#')):
                continue
            bound = (destination.parent / target.split('#')[0]).resolve()
            assert bound.is_relative_to(output.resolve())
            assert bound.is_file()
    assert '[PIPELINE.md](PIPELINE.md)' not in (output / 'docs/REWRITE_PLAN.md').read_text()
    assert 'PIPELINE.md' in (output / 'docs/REWRITE_PLAN.md').read_text()
    assert 'model_demo_summary.json' in (output / 'docs/MODELING_CONTRACT.md').read_text()
    assert '](../research/rewrite_completion_2026_11_02/model_demo_summary.json)' not in (
        output / 'docs/MODELING_CONTRACT.md').read_text()



def test_plan_snapshot_identity_uses_raw_bytes_not_canonical_json(run_files, exploratory_files):
    report, math, models, output = run_files
    data = json.loads(exploratory_files.read_text())
    plan_path = exploratory_files.parent / data['artifacts']['plan']['path']
    plan_path.write_text(json.dumps(json.loads(plan_path.read_text()), indent=3) + '\n\n')
    raw = plan_path.read_bytes()
    raw_hash = sha256(raw).hexdigest()
    data['artifacts']['plan'].update(sha256=raw_hash, bytes=len(raw))
    data['plan_sha256'] = raw_hash
    result_path = exploratory_files.parent / data['artifacts']['model_result']['path']
    result = json.loads(result_path.read_text())
    result['plan_sha256'] = raw_hash
    data['artifacts']['model_result'] = write_json(result_path, result)
    write_json(exploratory_files, data)
    payload = json.loads(export(report, math, models, output,
                                exploratory=exploratory_files).read_text())
    assert payload['exploratory']['report']['plan_sha256'] == raw_hash


@pytest.mark.parametrize('role', ['report', 'model_result'])
def test_wrong_plan_digest_rejected_even_with_matching_artifact_binding(run_files, exploratory_files, role):
    report, math, models, output = run_files
    data = json.loads(exploratory_files.read_text())
    if role == 'report':
        data['plan_sha256'] = '0' * 64
    else:
        result_path = exploratory_files.parent / data['artifacts'][role]['path']
        result = json.loads(result_path.read_text())
        result['plan_sha256'] = '0' * 64
        data['artifacts'][role] = write_json(result_path, result)
    write_json(exploratory_files, data)
    with pytest.raises(ValueError, match='identity mismatch'):
        export(report, math, models, output, exploratory=exploratory_files)
    assert not output.exists()


def test_bundled_methods_preserve_external_and_available_links_only():
    text = ('[methods](EXPLORATORY_ANALYSIS.md) [old](../STATUS.md) '
            '[external](https://example.org/study) [section](#selection) '
            '[source](../research/large/raw.json)')
    result = bundled_markdown(text, 'docs/REWRITE_PLAN.md')
    assert result == ('[methods](EXPLORATORY_ANALYSIS.md) old '
                      '[external](https://example.org/study) [section](#selection) source')
