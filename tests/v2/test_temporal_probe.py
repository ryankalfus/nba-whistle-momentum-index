"""Synthetic pixels test provenance and failure modes, never scientific validity."""
from copy import deepcopy
import json

import pytest
from PIL import Image

from research.ai_temporal_2026_11_07 import summarize_probe as probe
from whistle_research import ai_review as ar


@pytest.fixture
def evidence(tmp_path):
    game = json.loads(ar.CATALOG.read_bytes())['games'][0]
    declaration = dict(root='/private/coordinator/original', frames=[], schema_version=probe.SCHEMA,
        game_id=game['game_id'], date=game['date'], public_url=game['candidate_game_url'],
        catalog_sha256=ar.CATALOG_SHA256, audio_captured=False, full_game_review_completed=False,
        continuous_game_coverage_verified=False, prospective_test=dict(
            declared_at='2026-11-07T09:59:00Z', duration_target_seconds=20, frame_limit=300,
            collection='synthetic serial screenshots', engineering_target_max_adjacent_media_gap_seconds=1,
            engineering_target_is_not_scientific_validation=True, unknown_pixel_to_media_synchronization=True))
    capture = dict(deepcopy(declaration), started_at='2026-11-07T10:00:00Z',
                   started_ms=1794045600000, ended_at='2026-11-07T10:00:02Z')

    def observation(second, media, scroll=0, paused=False):
        return dict(observed_at=f'2026-11-07T10:00:{second:06.3f}Z',
            dom=dict(scrollY=scroll, url=game['candidate_game_url'], video=dict(currentTime=media,
                duration=100, error_code=None, height=720, width=1280, paused=paused, readyState=4)),
            visible_slider_value=str(media - .1))

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    for i in range(2):
        path = frames_dir / f'{i:04d}.png'
        Image.new('RGB', (12, 8), 'black').save(path)
        data = path.read_bytes()
        capture['frames'].append(dict(frame_id=f'{i:04d}', path=f'frames/{i:04d}.png',
            bytes=len(data), sha256=ar.digest(data), pre=observation(i, 10+i*.4),
            post=observation(i+.3, 10.2+i*.4),
            screenshot_requested_at=f'2026-11-07T10:00:0{i}.100Z',
            screenshot_returned_at=f'2026-11-07T10:00:0{i}.200Z'))
    capture['final_state'] = observation(2.5, 11, paused=True)
    return tmp_path, capture, declaration


def write(evidence, jsonl=True):
    root, capture, declaration = evidence
    (root / 'capture.json').write_bytes(ar.encoded(capture))
    (root / 'declared-test.json').write_bytes(ar.encoded(declaration))
    if jsonl:
        (root / 'frames.jsonl').write_text(''.join(json.dumps(f)+'\n' for f in capture['frames']))
    return root


def run(evidence, jsonl=True, catalog=ar.CATALOG):
    root = write(evidence, jsonl)
    return probe.summarize(root/'capture.json', root/'declared-test.json', catalog, root/'receipt')


def test_verified_receipt_has_no_scientific_promotion_or_private_root(evidence):
    report = run(evidence)
    assert report['frame_count'] == 2
    assert report['distinct_image_hashes'] == 1
    assert report['actual_media_metadata_span_seconds'] == pytest.approx(.6)
    assert report['actual_frame_wall_span_seconds'] == 1.3
    assert report['adjacent_midpoint_media_gaps_seconds'] == pytest.approx([.4])
    assert report['adjacent_metadata_gap_bounds_seconds'] == pytest.approx([.6])
    assert report['frames'][0]['media_bracket_width_seconds'] == pytest.approx(.2)
    assert report['prospective_engineering_criterion']['all_metadata_bounds_within_target'] is True
    assert report['metadata_checks_pass'] is True
    assert report['target_duration_met'] is False
    assert report['final_state_quality_issues'] == ['paused']
    assert report['scope'] == 'temporal_capture_feasibility'
    for key in ('audio', 'full_game_review_completed', 'continuous_game_coverage_verified',
                'scientific_approval', 'eligibility_promoted', 'complete_possession_verified',
                'pixel_to_media_synchronization_verified'):
        assert report[key] is False
    text = (evidence[0]/'receipt/summary.json').read_text()
    assert '/private' not in text and str(evidence[0]) not in text
    assert {i['role'] for i in report['consumed_inputs']} >= {
        'summarizer_code', 'provenance_helpers_code', 'capture', 'declaration',
        'selected_game_catalog', 'frames_jsonl', 'frame_0000_image', 'frame_0001_image'}


def test_quality_failures_retained_and_do_not_pass_metadata_checks(evidence):
    for frame in evidence[1]['frames']:
        for side in ('pre', 'post'):
            obs = frame[side]
            obs['dom']['scrollY'] = 278.5
            obs['dom']['video'].update(readyState=0, paused=True, error_code=3, width=0)
    report = run(evidence)
    assert report['frame_count'] == 2
    assert report['metadata_checks_pass'] is False
    assert report['prospective_engineering_criterion']['required_scrollY'] is None
    assert report['quality_issue_counts'] == dict(nonzero_scroll_alignment_unverified=2,
        paused=2, not_ready=2, media_error=2, missing_video_dimensions=2)
    assert report['frames'][0]['pre']['dom']['scrollY'] == 278.5


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(date='1900-01-01'),
    lambda c: c.update(game_id='0022999999'),
    lambda c: c.update(public_url='https://www.nba.com/other'),
    lambda c: c.update(full_game_review_completed=True),
    lambda c: c['prospective_test'].update(declared_at='2026-11-07T10:00:01Z'),
    lambda c: c['prospective_test'].update(engineering_target_max_adjacent_media_gap_seconds=True),
    lambda c: c['frames'][0].update(frame_id='0001'),
    lambda c: c['frames'][1].update(frame_id='0000'),
    lambda c: c['frames'][0].update(path='../outside.png'),
    lambda c: c['frames'][0].update(path='/private/picture.png'),
    lambda c: c['frames'][0].update(bytes=True),
    lambda c: c['frames'][0].update(sha256='0'*64),
    lambda c: c['frames'][0]['pre']['dom']['video'].update(currentTime=True),
    lambda c: c['frames'][0]['pre']['dom']['video'].update(currentTime=float('inf')),
    lambda c: c['frames'][0]['post']['dom']['video'].update(currentTime=9),
    lambda c: c['frames'][1]['pre']['dom']['video'].update(currentTime=9),
    lambda c: c['frames'][0]['post']['dom']['video'].update(duration=101),
    lambda c: c['frames'][0]['post']['dom'].update(url='https://nba.com/other'),
    lambda c: c['frames'][0].update(screenshot_returned_at='2026-11-07T10:00:00.000Z'),
    lambda c: c['frames'][0]['pre'].update(observed_at='2026-11-07T10:00:00'),
    lambda c: c['frames'][1]['pre'].update(observed_at='2026-11-07T10:00:00.200Z'),
    lambda c: c['final_state'].update(observed_at='2026-11-07T10:00:01Z'),
])
def test_false_or_malformed_evidence_rejected(evidence, mutation):
    mutation(evidence[1])
    # Equal top-level declarations must still fail the typed evidence checks.
    for key in probe.BASE-{'frames'}:
        evidence[2][key] = deepcopy(evidence[1][key])
    # Permit JSON's nonfinite token here to test the strict reader itself.
    root = write(evidence, jsonl=False) if 'inf' not in str(evidence[1]) else evidence[0]
    if 'inf' in str(evidence[1]):
        (root/'capture.json').write_text(json.dumps(evidence[1]))
        (root/'declared-test.json').write_text(json.dumps(evidence[2]))
    with pytest.raises(ValueError):
        probe.summarize(root/'capture.json', root/'declared-test.json', ar.CATALOG, root/'receipt')
    assert not (root/'receipt').exists()


def test_jsonl_mismatch_rejected(evidence):
    root = write(evidence)
    (root/'frames.jsonl').write_text(json.dumps(evidence[1]['frames'][0])+'\n')
    with pytest.raises(ValueError, match='frames.jsonl mismatch'):
        probe.summarize(root/'capture.json', root/'declared-test.json', ar.CATALOG, root/'receipt')


def test_catalog_drift_rejected(evidence):
    changed = evidence[0]/'catalog.json'
    changed.write_bytes(ar.CATALOG.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='catalog hash mismatch'):
        run(evidence, catalog=changed)


def test_existing_output_preserved(evidence):
    root = evidence[0]
    (root/'receipt').mkdir()
    (root/'receipt/keep').write_text('original')
    with pytest.raises(ValueError, match='output must be new'):
        run(evidence)
    assert (root/'receipt/keep').read_text() == 'original'


def test_image_corruption_with_updated_hash_is_rejected(evidence):
    path = evidence[0]/'frames/0000.png'
    data = path.read_bytes()[:40]
    path.write_bytes(data)
    evidence[1]['frames'][0].update(bytes=len(data), sha256=ar.digest(data))
    with pytest.raises((ValueError, OSError, SyntaxError)):
        run(evidence)
    assert not (evidence[0]/'receipt').exists()


def test_symlink_escape_rejected(evidence):
    root = evidence[0]
    original = root/'frames/0000.png'
    outside = root.parent/'outside.png'
    outside.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(outside)
    with pytest.raises(ValueError, match='symlink escape'):
        run(evidence)


def test_input_drift_during_verification_rejected(evidence, monkeypatch):
    original = ar.image_info

    def drift(data):
        path = evidence[0]/'capture.json'
        path.write_bytes(path.read_bytes()+b' ')
        return original(data)

    monkeypatch.setattr(ar, 'image_info', drift)
    with pytest.raises(ValueError, match='input drift'):
        run(evidence)
    assert not (evidence[0]/'receipt').exists()


def test_declaration_disagreement_and_duplicate_json_keys_rejected(evidence):
    evidence[2]['prospective_test']['duration_target_seconds'] = 30
    with pytest.raises(ValueError, match='capture/declaration mismatch'):
        run(evidence)
    root = write(evidence)
    raw = (root/'capture.json').read_bytes()
    (root/'capture.json').write_bytes(raw.replace(b'{', b'{"game_id":"fake",', 1))
    with pytest.raises(ValueError, match='duplicate JSON key'):
        probe.summarize(root/'capture.json', root/'declared-test.json', ar.CATALOG, root/'receipt')


def test_engineering_gap_failure_is_not_a_scientific_threshold(evidence):
    for value in evidence[1:]:
        value['prospective_test']['engineering_target_max_adjacent_media_gap_seconds'] = .5
    report = run(evidence)
    assert report['frame_count'] == 2
    assert report['metadata_checks_pass'] is False
    assert report['prospective_engineering_criterion']['all_metadata_bounds_within_target'] is False
    assert report['prospective_engineering_criterion']['scientific_error_threshold'] is False
    assert report['scientific_approval'] is False


def test_post_capture_obstruction_note_is_separate_and_byte_bound(evidence):
    root = evidence[0]
    (root/'quality-note.json').write_text(json.dumps(dict(status='obstructed_player',
        reason='Observed website header obscured player', all_frames_retained=True,
        full_game_review_completed=False)))
    report = run(evidence)
    assert report['post_capture_quality_note']['status'] == 'obstructed_player'
    assert report['post_capture_quality_note']['prospective'] is False
    assert report['reported_player_obstruction'] is True
    assert report['metadata_checks_pass'] is True
    assert report['prospective_engineering_criterion']['required_scrollY'] is None
    assert 'post_capture_quality_note' in {i['role'] for i in report['consumed_inputs']}


@pytest.mark.parametrize('suffix,accepted', [
    ('', True), ('?watchFullGame=true', True), ('?watchFullGame=false', False),
    ('?watchFullGame=true&other=1', False), ('?other=1', False), ('#watchFullGame=true', False),
    ('?watchFullGame=True', False), ('/?watchFullGame=true', False),
])
def test_exact_catalog_url_or_single_explicit_player_suffix(evidence, suffix, accepted):
    url = evidence[1]['public_url']+suffix
    for value in evidence[1:]:
        value['public_url'] = url
    for frame in evidence[1]['frames']:
        for side in ('pre', 'post'):
            frame[side]['dom']['url'] = url
    evidence[1]['final_state']['dom']['url'] = url
    if accepted:
        report = run(evidence)
        assert report['captured_public_url'] == url
        assert report['catalog_public_url']+suffix == url
        assert '?watchFullGame=true only' in report['public_url_identity_rule']
    else:
        with pytest.raises(ValueError, match='game identity mismatch'):
            run(evidence)


@pytest.mark.parametrize('final_media', [10, 11])
def test_stationary_capture_fails_metadata_checks_despite_ready_playing_state(evidence, final_media):
    for value in evidence[1:]:
        value['prospective_test']['duration_target_seconds'] = 2
    for frame in evidence[1]['frames']:
        for side in ('pre', 'post'):
            frame[side]['dom']['video']['currentTime'] = 10
    # Progress after collection ends cannot rescue stationary captured evidence.
    evidence[1]['final_state']['dom']['video']['currentTime'] = final_media
    report = run(evidence)
    assert report['target_duration_met'] is True
    assert report['frame_count'] == 2
    assert report['frames_with_quality_issues'] == 0
    assert report['actual_media_metadata_span_seconds'] == 0
    assert report['prospective_engineering_criterion']['all_metadata_bounds_within_target'] is True
    assert report['metadata_checks_pass'] is False
    assert report['run_metadata_issues'] == ['no_media_progress']
    for key in ('full_game_review_completed', 'continuous_game_coverage_verified',
                'scientific_approval', 'eligibility_promoted'):
        assert report[key] is False


def test_short_stationary_bracket_and_duplicate_image_do_not_fail_advancing_run(evidence):
    first = evidence[1]['frames'][0]
    first['post']['dom']['video']['currentTime'] = first['pre']['dom']['video']['currentTime']
    report = run(evidence)
    assert report['frames'][0]['media_bracket_width_seconds'] == 0
    assert report['distinct_image_hashes'] == 1
    assert report['actual_media_metadata_span_seconds'] > 0
    assert report['run_metadata_issues'] == []
    assert report['metadata_checks_pass'] is True
    assert report['frame_count'] == 2
