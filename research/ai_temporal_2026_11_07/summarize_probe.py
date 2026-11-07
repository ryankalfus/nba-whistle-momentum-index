"""Offline development receipt for temporal capture probes, never an audit gate."""
import argparse
import math
from pathlib import Path

from whistle_research import ai_review as ar


SCHEMA = 'temporal-capture-feasibility-v1'
FLAGS = ('audio_captured', 'full_game_review_completed', 'continuous_game_coverage_verified')
BASE = {'root', 'frames', 'schema_version', 'game_id', 'date', 'public_url',
        'catalog_sha256', 'prospective_test', *FLAGS}


def number(value, minimum=None):
    ar.require(type(value) in (int, float) and math.isfinite(value), 'finite numeric value required')
    ar.require(minimum is None or value >= minimum, 'numeric value below minimum')
    return value


def observation(value, url, duration):
    ar.require(set(value) == {'observed_at', 'dom', 'visible_slider_value'}, 'observation fields')
    observed = ar.timestamp(value['observed_at'])
    dom = value['dom']
    ar.require(set(dom) == {'scrollY', 'url', 'video'} and dom['url'] == url, 'observation URL/fields')
    number(dom['scrollY'])
    video = dom['video']
    ar.require(set(video) == {'currentTime', 'duration', 'error_code', 'height', 'paused',
                              'readyState', 'width'}, 'video fields')
    position = number(video['currentTime'], 0)
    runtime = number(video['duration'], 0)
    ar.require(position <= runtime and runtime > 0, 'media time bounds')
    ar.require(duration is None or runtime == duration, 'runtime changed')
    ar.require(type(video['paused']) is bool, 'paused must be bool')
    ar.require(ar.integer(video['readyState'], 0) and video['readyState'] <= 4, 'readyState invalid')
    for key in ('width', 'height'):
        ar.require(ar.integer(video[key], 0), 'video dimensions invalid')
    ar.require(video['error_code'] is None or
               (ar.integer(video['error_code'], 1) and video['error_code'] <= 4), 'media error invalid')
    slider = value['visible_slider_value']
    ar.require(isinstance(slider, str), 'slider must be a string')
    number(float(slider), 0)
    issues = []
    if dom['scrollY'] != 0:
        issues.append('nonzero_scroll_alignment_unverified')
    if video['paused']:
        issues.append('paused')
    if video['readyState'] < 2:
        issues.append('not_ready')
    if video['error_code'] is not None:
        issues.append('media_error')
    if min(video['width'], video['height']) == 0:
        issues.append('missing_video_dimensions')
    return observed, position, runtime, issues


def summarize(capture, declaration, catalog, output):
    """Verify evidence bytes before publishing a new, non-promoting receipt."""
    inputs = ar.Inputs()
    roles = {}

    def read(path, role):
        path = Path(path).absolute()
        data = inputs.read(path)
        roles[path] = role
        return data

    read(Path(__file__), 'summarizer_code')
    read(Path(ar.__file__), 'provenance_helpers_code')
    capture, declaration, catalog = Path(capture), Path(declaration), Path(catalog)
    ar.require(not Path(output).exists(), 'output must be new')
    value = ar.strict_json(read(capture, 'capture'))
    declared = ar.strict_json(read(declaration, 'declaration'))
    ar.require(set(declared) == BASE, 'declaration fields')
    ar.require(set(value) == BASE | {'started_at', 'started_ms', 'ended_at', 'final_state'}, 'capture fields')
    ar.require(declared['frames'] == [], 'declaration must precede collection')
    for key in BASE - {'frames'}:
        ar.require(value[key] == declared[key], f'capture/declaration mismatch: {key}')
    ar.require(value['schema_version'] == SCHEMA, 'schema mismatch')
    for flag in FLAGS:
        ar.require(value[flag] is False and declared[flag] is False, 'coverage/audio claim forbidden')
    raw_catalog = read(catalog, 'selected_game_catalog')
    ar.require(ar.digest(raw_catalog) == ar.CATALOG_SHA256 == value['catalog_sha256'], 'catalog hash mismatch')
    selected = [g for g in ar.strict_json(raw_catalog)['games'] if g['game_id'] == value['game_id']]
    ar.require(len(selected) == 1, 'game not uniquely selected')
    catalog_url = selected[0]['candidate_game_url']
    ar.require(value['date'] == selected[0]['date'] and
               value['public_url'] in (catalog_url, catalog_url + '?watchFullGame=true'),
               'game identity mismatch')
    plan = declared['prospective_test']
    plan_keys = {'declared_at', 'duration_target_seconds', 'frame_limit', 'collection',
                 'engineering_target_max_adjacent_media_gap_seconds',
                 'engineering_target_is_not_scientific_validation', 'unknown_pixel_to_media_synchronization'}
    ar.require(set(plan) in (plan_keys, plan_keys | {'required_scrollY'}), 'prospective fields')
    ar.require(plan['engineering_target_is_not_scientific_validation'] is True and
               plan['unknown_pixel_to_media_synchronization'] is True, 'prospective limits required')
    ar.require(isinstance(plan['collection'], str) and plan['collection'], 'collection method required')
    target = number(plan['engineering_target_max_adjacent_media_gap_seconds'], 0)
    ar.require(target > 0 and number(plan['duration_target_seconds'], 0) > 0, 'positive target required')
    ar.require(ar.integer(plan['frame_limit'], 1), 'frame limit invalid')
    if 'required_scrollY' in plan:
        number(plan['required_scrollY'])
    start, end = ar.timestamp(value['started_at']), ar.timestamp(value['ended_at'])
    ar.require(ar.timestamp(plan['declared_at']) < start <= end, 'declaration must be prospective')
    ar.require(ar.integer(value['started_ms'], 0) and
               abs(value['started_ms'] - start.timestamp() * 1000) <= 1.01, 'start clocks disagree')
    frames = value['frames']
    ar.require(isinstance(frames, list) and 0 < len(frames) <= plan['frame_limit'], 'frame count invalid')
    jsonl = capture.parent / 'frames.jsonl'
    if jsonl.exists():
        rows = [ar.strict_json(line) for line in read(jsonl, 'frames_jsonl').splitlines()]
        ar.require(rows == frames, 'frames.jsonl mismatch')
    quality_note = None
    note_path = capture.parent / 'quality-note.json'
    if note_path.exists():
        note = ar.strict_json(read(note_path, 'post_capture_quality_note'))
        ar.require(set(note) == {'status', 'reason', 'all_frames_retained', 'full_game_review_completed'},
                   'quality note fields')
        ar.require(note['status'] == 'obstructed_player' and isinstance(note['reason'], str) and
                   note['all_frames_retained'] is True and note['full_game_review_completed'] is False,
                   'quality note claim invalid')
        quality_note = dict(status=note['status'], prospective=False,
                            interpretation='Post-capture note reports player/header obstruction; all frames retained.')
    results, duration, previous_wall, previous_media = [], None, start, 0
    midpoints, bounds = [], []
    for i, frame in enumerate(frames):
        ar.require(set(frame) == {'frame_id', 'pre', 'post', 'screenshot_requested_at',
                                  'screenshot_returned_at', 'path', 'bytes', 'sha256'}, 'frame fields')
        fid = f'{i:04d}'
        ar.require(frame['frame_id'] == fid, 'ordered consecutive frame IDs required')
        pre, before, duration, issues_pre = observation(frame['pre'], value['public_url'], duration)
        post, after, _, issues_post = observation(frame['post'], value['public_url'], duration)
        requested = ar.timestamp(frame['screenshot_requested_at'])
        returned = ar.timestamp(frame['screenshot_returned_at'])
        ar.require(previous_wall <= pre <= requested <= returned <= post <= end, 'screenshot chronology')
        ar.require(previous_media <= before <= after, 'media chronology')
        previous_wall, previous_media = post, after
        image_path = ar.safe_path(capture.parent, frame['path'])
        data = read(image_path, f'frame_{fid}_image')
        ar.require(ar.integer(frame['bytes'], 1) and frame['bytes'] == len(data), 'image byte count mismatch')
        ar.require(frame['sha256'] == ar.digest(data), 'image hash mismatch')
        image_format, dimensions = ar.image_info(data)
        issues = sorted(set(issues_pre + issues_post))
        if 'required_scrollY' in plan and any(
                frame[side]['dom']['scrollY'] != plan['required_scrollY'] for side in ('pre', 'post')):
            issues.append('declared_alignment_requirement_failed')
        midpoint = (before + after) / 2
        if results:
            midpoints.append(midpoint - results[-1]['media_midpoint_seconds'])
            bounds.append(after - results[-1]['media_pre_seconds'])
        results.append(dict(frame_id=fid, path=frame['path'], bytes=len(data), sha256=ar.digest(data),
            image_format=image_format, dimensions=dimensions,
            pre=frame['pre'], post=frame['post'], screenshot_requested_at=frame['screenshot_requested_at'],
            screenshot_returned_at=frame['screenshot_returned_at'], media_pre_seconds=before,
            media_post_seconds=after, media_midpoint_seconds=midpoint,
            media_bracket_width_seconds=after-before, wall_bracket_width_seconds=(post-pre).total_seconds(),
            slider_lag_seconds_descriptive={side: frame[side]['dom']['video']['currentTime'] -
                float(frame[side]['visible_slider_value']) for side in ('pre', 'post')}, quality_issues=issues))
    final_at, final_media, _, final_issues = observation(value['final_state'], value['public_url'], duration)
    ar.require(end <= final_at and final_media >= previous_media, 'final state chronology')
    counts = {issue: sum(issue in f['quality_issues'] for f in results)
              for issue in sorted({issue for f in results for issue in f['quality_issues']})}
    media_span = results[-1]['media_post_seconds'] - results[0]['media_pre_seconds']
    run_issues = ['no_media_progress'] if media_span == 0 else []
    report = dict(schema_version='temporal-probe-receipt-v1', scope='temporal_capture_feasibility',
        **{key: value[key] for key in ('game_id', 'date', 'public_url')},
        audio=False, full_game_review_completed=False, continuous_game_coverage_verified=False,
        scientific_approval=False, eligibility_promoted=False, complete_possession_verified=False,
        pixel_to_media_synchronization_verified=False,
        limitations=['Metadata bounds do not verify pixel timing or continuous footage.',
                     'No scientific accuracy, error bound, independent audit or eligibility is established.',
                     'Nonzero scroll is an alignment issue; zero scroll alone does not prove unobstructed pixels.'],
        frame_count=len(results), distinct_image_hashes=len({f['sha256'] for f in results}),
        frames_with_quality_issues=sum(bool(f['quality_issues']) for f in results), quality_issue_counts=counts,
        run_metadata_issues=run_issues,
        metadata_checks_pass=not counts and not run_issues and bool(bounds) and max(bounds) <= target,
        target_duration_met=(end-start).total_seconds() >= plan['duration_target_seconds'],
        reported_player_obstruction=quality_note is not None,
        catalog_public_url=catalog_url, captured_public_url=value['public_url'],
        public_url_identity_rule='Exact catalog URL or exact catalog URL plus ?watchFullGame=true only',
        post_capture_quality_note=quality_note,
        started_at=value['started_at'], ended_at=value['ended_at'],
        actual_run_wall_span_seconds=(end-start).total_seconds(),
        actual_frame_wall_span_seconds=(previous_wall-ar.timestamp(frames[0]['pre']['observed_at'])).total_seconds(),
        actual_media_metadata_span_seconds=media_span,
        adjacent_midpoint_media_gaps_seconds=midpoints,
        adjacent_metadata_gap_bounds_seconds=bounds,
        metadata_gap_bound_definition='next post media time minus previous pre media time; pixel synchronization unverified',
        prospective_engineering_criterion=dict(declared_at=plan['declared_at'],
            max_adjacent_media_gap_seconds=target, duration_target_seconds=plan['duration_target_seconds'],
            frame_limit=plan['frame_limit'], required_scrollY=plan.get('required_scrollY'),
            scientific_error_threshold=False,
            all_metadata_bounds_within_target=bool(bounds) and max(bounds) <= target),
        final_state=value['final_state'], final_state_quality_issues=final_issues, frames=results)
    report['consumed_inputs'] = [dict(role=roles[path], bytes=len(data), sha256=ar.digest(data))
                                 for path, data in inputs.items.items()]
    ar.publish(output, {'summary.json': ar.encoded(report)}, inputs)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('capture', 'declaration', 'catalog', 'output'):
        parser.add_argument(f'--{flag}', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = summarize(args.capture, args.declaration, args.catalog, args.output)
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as error:
        parser.exit(2, f'Invalid probe evidence: {error}\n')
    print(f"Verified {report['frame_count']} frames; scope={report['scope']}; scientific_approval=false")


if __name__ == '__main__':
    main()
