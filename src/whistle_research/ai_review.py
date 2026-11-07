"""Strict, isolated AI sampled-frame review; never a human scientific audit."""
import argparse
import hashlib
import io
import json
import math
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2] / 'research/audit_access_2026_11_06/catalog.json'
CATALOG_SHA256 = '06aa44fb27877752a7044acf13a0a8b73b0c792a230236cf2b22017abed4a7b4'
FIELDS = ('period', 'clock', 'away_score', 'home_score', 'ball_control', 'visible_event')
LIMITS = ['Matching AI labels are not truth; distinct agent IDs are not statistical independence.',
          'Same-model errors may be shared.',
          'Sampled frames lack audio, continuous coverage and complete event coverage.',
          'Metadata surrounds screenshots; pixel/video-time synchronization is not guaranteed.',
          'No game material-error rate or 1% bound can be inferred.',
          'No scientific approval, eligibility or human audit completion is conferred.']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f'duplicate JSON key: {key}')
            out[key] = value
        return out

    def invalid(value):
        raise ValueError(f'nonfinite JSON number: {value}')

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


class Inputs:
    def __init__(self):
        self.items = {}

    def read(self, path):
        path = Path(path).absolute()
        data = path.read_bytes()
        require(path not in self.items or self.items[path] == data, 'input drift')
        self.items[path] = data
        return data

    def check(self):
        for path, data in self.items.items():
            require(path.read_bytes() == data, f'input drift: {path.name}')

    def receipt(self, output):
        return [{'role': f'input_{i}', 'path': os.path.relpath(p, Path(output).absolute()), 'bytes': len(b), 'sha256': digest(b)}
                for i, (p, b) in enumerate(self.items.items())]


def safe_path(root, value):
    require(isinstance(value, str) and value and '\\' not in value, 'invalid path')
    part = Path(value)
    require(not part.is_absolute() and '..' not in part.parts, 'unsafe path')
    target = root / part
    require(target.resolve().is_relative_to(root.resolve()), 'symlink escape')
    return target


def timestamp(value):
    require(isinstance(value, str), 'timestamp required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.utcoffset() is not None, 'timezone required')
    return parsed


def integer(value, minimum):
    return type(value) is int and value >= minimum


def common_frame(frame):
    require(isinstance(frame, dict), 'frame object required')
    fid = frame['frame_id']
    require(isinstance(fid, str) and re.fullmatch(r'[A-Za-z0-9_-]+', fid), 'invalid frame ID')
    require(integer(frame['bytes'], 1), 'positive integer image bytes required')
    require(isinstance(frame['sha256'], str) and re.fullmatch(r'[a-f0-9]{64}', frame['sha256']),
            'canonical SHA256 required')
    timestamp(frame['captured_at'])
    for key in ('video_time_seconds', 'duration_seconds'):
        require(type(frame[key]) in (int, float) and math.isfinite(frame[key]), 'finite time required')
    require(0 <= frame['video_time_seconds'] < frame['duration_seconds'], 'invalid time bounds')


def coverage_counts(frames):
    return dict(frame_count=len(frames), unique_image_hashes=len({f['sha256'] for f in frames}),
                unique_video_positions=len({f['video_time_seconds'] for f in frames}),
                unique_image_position_pairs=len({(f['sha256'], f['video_time_seconds']) for f in frames}))


def image_info(data):
    from PIL import Image

    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        expected = 'PNG'
    elif data.startswith(b'\xff\xd8\xff'):
        expected = 'JPEG'
    else:
        raise ValueError('PNG or JPEG signature required')
    with Image.open(io.BytesIO(data)) as image:
        require(image.format == expected and min(image.size) > 0, 'invalid image format/dimensions')
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return expected, list(image.size)


def identity(value, inputs, catalog):
    raw = inputs.read(catalog)
    require(digest(raw) == CATALOG_SHA256, 'catalog hash mismatch')
    catalog = strict_json(raw)
    games = [g for g in catalog['games'] if g['game_id'] == value['game_id']]
    require(len(games) == 1, 'game not uniquely selected')
    require(value['date'] == games[0]['date'], 'wrong game date')
    require(value['public_url'] == games[0]['candidate_game_url'], 'wrong/private game URL')
    return {key: value[key] for key in ('game_id', 'date', 'public_url')}


def boundary(value):
    require(value.get('scope') == 'sampled_frames', 'sampled-frame scope required')
    require(value.get('continuous_coverage_verified', False) is False, 'continuous claim forbidden')
    require(value.get('research_gate_authorized', False) is False, 'science approval forbidden')


def publish(output, files, inputs):
    output = Path(output)
    require(not output.exists(), 'output must be new')
    inputs.check()
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files.items():
            target = safe_path(output, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        inputs.check()
    except BaseException:
        shutil.rmtree(output)
        raise


def prepare(capture, output, catalog=CATALOG):
    inputs = Inputs()
    inputs.read(Path(__file__))
    capture = Path(capture)
    value = strict_json(inputs.read(capture))
    require(value.get('schema_version') == 'ai-frame-capture-v1', 'capture schema mismatch')
    require(set(value) == {'schema_version', 'scope', 'game_id', 'date', 'public_url',
                           'audio_available', 'continuous_coverage_verified', 'frames'},
            'unexpected/missing capture fields')
    boundary(value)
    require(value.get('audio_available') is False, 'audio unavailable required')
    packet = dict(schema_version='ai-frame-packet-v1', scope='sampled_frames',
                  **identity(value, inputs, catalog), audio_available=False,
                  continuous_coverage_verified=False, frames=[], limits=LIMITS)
    require(isinstance(value['frames'], list) and value['frames'], 'frames required')
    files, ids = {}, set()
    for i, frame in enumerate(value['frames']):
        require(isinstance(frame, dict) and set(frame) == {'frame_id', 'path', 'bytes', 'sha256', 'captured_at',
                               'video_time_seconds', 'duration_seconds', 'video_ready_state',
                               'paused', 'media_error', 'video_width', 'video_height'},
                'unexpected/missing capture frame fields')
        fid = frame['frame_id']
        common_frame(frame)
        require(fid not in ids, 'duplicate frame ID')
        ids.add(fid)
        require(integer(frame['video_ready_state'], 2) and frame['video_ready_state'] <= 4,
                'video not ready')
        require(type(frame['paused']) is bool and frame['media_error'] is None, 'invalid media state')
        require(all(integer(frame[k], 1) for k in ('video_width', 'video_height')), 'video dimensions')
        data = inputs.read(safe_path(capture.parent, frame['path']))
        require(type(frame['bytes']) is int and frame['bytes'] == len(data), 'image bytes mismatch')
        require(frame['sha256'] == digest(data), 'image hash mismatch')
        image_format, dimensions = image_info(data)
        extension = 'png' if image_format == 'PNG' else 'jpg'
        name = f'frames/{i:04d}.{extension}'
        files[name] = data
        packet['frames'].append(dict(frame_id=fid, path=name, bytes=len(data),
                                     sha256=digest(data), dimensions=dimensions, image_format=image_format,
                                     **{k: frame[k] for k in ('captured_at', 'video_time_seconds',
                                                              'duration_seconds')}))
    packet['coverage_counts'] = coverage_counts(packet['frames'])
    packet_bytes = encoded(packet)
    files['packet.json'] = packet_bytes
    for slot in ('A', 'B'):
        template = dict(schema_version='ai-frame-review-v1', reviewer_kind='ai', slot=slot,
                        model=None, agent_id=None, started_at=None, completed_at=None,
                        packet_sha256=digest(packet_bytes), scope='sampled_frames',
                        observations=[dict(frame_id=f['frame_id'], **dict.fromkeys(FIELDS),
                                           uncertain=None, notes=None) for f in packet['frames']])
        files[f'AI_{slot}.json'] = encoded(template)
    files['provenance.json'] = encoded(dict(inputs=inputs.receipt(output), packet_sha256=digest(packet_bytes)))
    publish(output, files, inputs)
    return packet


def review(value, slot, packet, packet_hash):
    allowed = {'schema_version', 'reviewer_kind', 'slot', 'model', 'agent_id', 'started_at',
               'completed_at', 'packet_sha256', 'scope', 'observations'}
    require(set(value) == allowed, 'unexpected/missing review fields')
    require(value['schema_version'] == 'ai-frame-review-v1' and value['reviewer_kind'] == 'ai',
            'AI review required')
    boundary(value)
    require(value['slot'] == slot and value['packet_sha256'] == packet_hash, 'cross-packet/slot review')
    for key in ('model', 'agent_id'):
        require(isinstance(value[key], str) and value[key] and value[key] == value[key].strip(),
                f'{key} required and must be trimmed')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value['agent_id']),
            'invalid agent ID')
    require(timestamp(value['started_at']) <= timestamp(value['completed_at']), 'review times reversed')
    observations = value['observations']
    require(isinstance(observations, list), 'observations required')
    require(len(observations) == len(packet['frames']), 'missing/duplicate frames')
    indexed = {}
    for obs in observations:
        require(set(obs) == {'frame_id', *FIELDS, 'uncertain', 'notes'}, 'observation fields mismatch')
        require(obs['frame_id'] not in indexed, 'duplicate observation')
        for key in ('period', 'away_score', 'home_score'):
            require(obs[key] is None or integer(obs[key], 1 if key == 'period' else 0), 'invalid integer')
        clock = obs['clock']
        require(clock is None or (isinstance(clock, str) and
                re.fullmatch(r'[0-9]{1,2}:[0-5][0-9](?:\.[0-9])?', clock)), 'invalid clock')
        require(obs['ball_control'] in ('away', 'home', 'dead_ball', 'unclear'), 'invalid control')
        require(obs['visible_event'] in ('jump_ball', 'shot', 'rebound', 'turnover', 'foul_signal',
                                         'free_throw', 'timeout', 'other', 'unclear'), 'invalid event')
        require(type(obs['uncertain']) is bool and isinstance(obs['notes'], str), 'incomplete observation')
        indexed[obs['frame_id']] = obs
    require(set(indexed) == {f['frame_id'] for f in packet['frames']}, 'frame IDs mismatch')
    return indexed


def clock_ticks(clock):
    """Compare valid visual clocks in integer tenths without changing source text."""
    minutes, seconds = clock.split(':')
    whole, _, fraction = seconds.partition('.')
    return int(minutes) * 600 + int(whole) * 10 + int(fraction or '0')


def compare(packet, review_a, review_b, output, catalog=CATALOG):
    inputs = Inputs()
    inputs.read(Path(__file__))
    packet = Path(packet)
    raw = inputs.read(packet)
    value = strict_json(raw)
    require(value.get('schema_version') == 'ai-frame-packet-v1', 'packet schema mismatch')
    require(set(value) == {'schema_version', 'scope', 'game_id', 'date', 'public_url',
                           'audio_available', 'continuous_coverage_verified', 'frames', 'limits', 'coverage_counts'},
            'unexpected/missing packet fields')
    require(value['audio_available'] is False and value['limits'] == LIMITS, 'packet limits mismatch')
    boundary(value)
    identity(value, inputs, catalog)
    require(isinstance(value['frames'], list) and value['frames'], 'frames list required')
    ids = set()
    for frame in value['frames']:
        require(isinstance(frame, dict) and set(frame) == {
            'frame_id', 'path', 'bytes', 'sha256', 'dimensions', 'image_format', 'captured_at',
            'video_time_seconds', 'duration_seconds'}, 'unexpected packet frame fields')
        common_frame(frame)
        require(frame['frame_id'] not in ids, 'duplicate frame ID')
        ids.add(frame['frame_id'])
        dimensions = frame['dimensions']
        require(type(dimensions) is list and len(dimensions) == 2 and
                all(integer(n, 1) for n in dimensions), 'integer image dimensions required')
        data = inputs.read(safe_path(packet.parent, frame['path']))
        require(len(data) == frame['bytes'] and digest(data) == frame['sha256'], 'packet image mismatch')
        image_format, actual_dimensions = image_info(data)
        require(frame['image_format'] in ('PNG', 'JPEG') and frame['image_format'] == image_format,
                'packet image format mismatch')
        require(actual_dimensions == dimensions, 'packet dimensions mismatch')
    require(encoded(value['coverage_counts']) == encoded(coverage_counts(value['frames'])),
            'coverage counts mismatch')
    a_raw, b_raw = inputs.read(review_a), inputs.read(review_b)
    a, b = strict_json(a_raw), strict_json(b_raw)
    aa, bb = review(a, 'A', value, digest(raw)), review(b, 'B', value, digest(raw))
    require(a['agent_id'].casefold() != b['agent_id'].casefold(), 'distinct AI agent IDs required')
    rows = []
    counts = dict(same=0, discordant=0, unknown=0)
    for fid in aa:
        fields = {}
        for field in FIELDS:
            x, y = aa[fid][field], bb[fid][field]
            if x in (None, 'unclear') or y in (None, 'unclear'):
                status = 'unknown'
            else:
                same = clock_ticks(x) == clock_ticks(y) if field == 'clock' else x == y
                status = 'same' if same else 'discordant'
            fields[field] = dict(a=x, b=y, status=status)
            counts[status] += 1
        rows.append(dict(frame_id=fid, fields=fields,
                         notes=dict(a=aa[fid]['notes'], b=bb[fid]['notes']),
                         uncertain=dict(a=aa[fid]['uncertain'], b=bb[fid]['uncertain'])))
    report = dict(schema_version='ai-frame-comparison-v1', scope='sampled_frames',
                  game_id=value['game_id'],
                  clock_comparison_normalization='M:SS or MM:SS with optional .t compared as integer tenths; original labels preserved',
                  research_gate_authorized=False,
                  human_reviews_completed=0, continuous_coverage_verified=False,
                  games_with_two_sampled_frame_reviews=1, coverage_counts=coverage_counts(value['frames']), counts=counts, frames=rows, limits=LIMITS)
    publish(output, {'report.json': encoded(report), 'provenance.json': encoded(dict(
        inputs=inputs.receipt(output), packet_sha256=digest(raw), review_a_sha256=digest(a_raw),
        review_b_sha256=digest(b_raw)))}, inputs)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--capture', required=True, type=Path)
    prep.add_argument('--output', required=True, type=Path)
    comp = sub.add_parser('compare')
    for flag in ('packet', 'review-a', 'review-b', 'output'):
        comp.add_argument('--' + flag, required=True, type=Path)
    for command_parser in (prep, comp):
        command_parser.add_argument('--catalog', type=Path, default=CATALOG)
    args = vars(parser.parse_args())
    command = args.pop('command')
    try:
        (prepare if command == 'prepare' else compare)(**args)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f'Invalid AI frame evidence: {exc}\n')


if __name__ == '__main__':
    main()
