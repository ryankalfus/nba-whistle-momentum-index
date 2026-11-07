"""Offline synthetic images test contracts, not visual truth or scientific validity."""
import json

import pytest
from PIL import Image

from whistle_research import ai_review as ar


@pytest.fixture
def capture(tmp_path):
    catalog = json.loads(ar.CATALOG.read_bytes())
    game = catalog['games'][0]
    image = tmp_path / 'frame.png'
    Image.new('RGB', (12, 8), 'black').save(image)
    data = image.read_bytes()
    frame = dict(frame_id='f1', path='frame.png', bytes=len(data), sha256=ar.digest(data),
                 captured_at='2026-11-06T10:00:00+00:00', video_time_seconds=1,
                 duration_seconds=100, video_ready_state=4, paused=True, media_error=None,
                 video_width=1920, video_height=1080)
    value = dict(schema_version='ai-frame-capture-v1', scope='sampled_frames',
                 game_id=game['game_id'], date=game['date'], public_url=game['candidate_game_url'],
                 audio_available=False, continuous_coverage_verified=False, frames=[frame])
    path = tmp_path / 'capture.json'
    path.write_bytes(ar.encoded(value))
    return path, value


def submissions(folder):
    for slot in ('A', 'B'):
        path = folder / f'AI_{slot}.json'
        value = json.loads(path.read_bytes())
        value.update(model='synthetic-test', agent_id=f'test-{slot}',
                     started_at='2026-11-06T10:00:00Z', completed_at='2026-11-06T10:01:00Z')
        value['observations'][0].update(period=1, clock=None, away_score=0, home_score=0,
                                        ball_control='unclear', visible_event='jump_ball',
                                        uncertain=True, notes='Synthetic fixture only')
        path.write_bytes(ar.encoded(value))


def run_compare(folder, output):
    return ar.compare(folder / 'packet.json', folder / 'AI_A.json', folder / 'AI_B.json', output)


def test_unknown_and_disagreement(capture, tmp_path):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    b = folder / 'AI_B.json'
    value = json.loads(b.read_bytes())
    value['observations'][0]['home_score'] = 2
    b.write_bytes(ar.encoded(value))
    report = run_compare(folder, tmp_path / 'comparison')
    assert report['counts'] == dict(same=3, discordant=1, unknown=2)
    assert report['human_reviews_completed'] == 0
    assert report['research_gate_authorized'] is False
    assert (folder / 'frames/0000.png').read_bytes() == (tmp_path / 'frame.png').read_bytes()


@pytest.mark.parametrize('field,value', [('date', '1900-01-01'), ('game_id', 'bad'),
    ('public_url', 'https://user:secret@nba.com/game/private')])
def test_identity_rejected(capture, tmp_path, field, value):
    path, obj = capture
    obj[field] = value
    path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        ar.prepare(path, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('field,value', [('sha256', '0' * 64), ('bytes', 1),
    ('path', '../frame.png'), ('path', '/private/frame.png'), ('duration_seconds', 0),
    ('video_ready_state', 1), ('media_error', 'failed')])
def test_bad_frames(capture, tmp_path, field, value):
    path, obj = capture
    obj['frames'][0][field] = value
    path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        ar.prepare(path, tmp_path / 'out')


@pytest.mark.parametrize('frames', [[], [0, 0]])
def test_missing_duplicate_frames(capture, tmp_path, frames):
    path, obj = capture
    obj['frames'] = [obj['frames'][i] for i in frames]
    path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        ar.prepare(path, tmp_path / 'out')


@pytest.mark.parametrize('field,value', [('reviewer_kind', 'human'), ('packet_sha256', 'x'),
    ('agent_id', 'test-A'), ('observations', [])])
def test_bad_reviews(capture, tmp_path, field, value):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    b = folder / 'AI_B.json'
    obj = json.loads(b.read_bytes())
    obj[field] = value
    b.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        run_compare(folder, tmp_path / 'result')
    assert not (tmp_path / 'result').exists()


def test_drift_and_fresh_directory(capture, tmp_path, monkeypatch):
    path, _ = capture
    original = ar.Inputs.check

    def drift(self):
        path.write_bytes(b'changed')
        original(self)

    monkeypatch.setattr(ar.Inputs, 'check', drift)
    with pytest.raises(ValueError, match='drift'):
        ar.prepare(path, tmp_path / 'new')
    assert not (tmp_path / 'new').exists()
    monkeypatch.setattr(ar.Inputs, 'check', original)
    with pytest.raises(ValueError, match='new'):
        ar.publish(tmp_path, {}, ar.Inputs())


def test_strict_json():
    for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
        with pytest.raises(ValueError):
            ar.strict_json(text)


def test_symlink_escape(capture, tmp_path):
    path, obj = capture
    (tmp_path / 'escape').symlink_to(tmp_path.parent, target_is_directory=True)
    obj['frames'][0]['path'] = 'escape/image.png'
    path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError, match='escape'):
        ar.prepare(path, tmp_path / 'out')


def test_tampered_packet_image(capture, tmp_path):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    (folder / 'frames/0000.png').write_bytes(b'forged')
    with pytest.raises(ValueError, match='image mismatch'):
        run_compare(folder, tmp_path / 'out')


def test_empty_templates_are_not_submissions(capture, tmp_path):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    with pytest.raises(ValueError, match='model required'):
        run_compare(folder, tmp_path / 'out')


def test_postwrite_drift_removes_new_output(tmp_path):
    class Drifting:
        calls = 0

        def check(self):
            self.calls += 1
            if self.calls == 2:
                raise ValueError('post-write drift')

    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='post-write drift'):
        ar.publish(output, {'packet.json': b'{}'}, Drifting())
    assert not output.exists()


@pytest.mark.parametrize('key,value', [('bytes', 77.0), ('dimensions', [12.0, 8.0]),
                                      ('frame_id', 1), ('sha256', 'A' * 64)])
def test_packet_typed_contract(capture, tmp_path, key, value):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    packet_path = folder / 'packet.json'
    obj = json.loads(packet_path.read_bytes())
    if key == 'bytes':
        value = float(obj['frames'][0]['bytes'])
    obj['frames'][0][key] = value
    packet_path.write_bytes(ar.encoded(obj))
    submissions(folder)
    for slot in ('A', 'B'):
        review_path = folder / f'AI_{slot}.json'
        obj = json.loads(review_path.read_bytes())
        obj['packet_sha256'] = ar.digest(packet_path.read_bytes())
        obj['observations'][0]['frame_id'] = json.loads(packet_path.read_bytes())['frames'][0]['frame_id']
        review_path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        run_compare(folder, tmp_path / 'out')


@pytest.mark.parametrize('agent_id', [' test-B ', 'TEST-A', 'invalid id'])
def test_canonical_agent_ids(capture, tmp_path, agent_id):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    b = folder / 'AI_B.json'
    obj = json.loads(b.read_bytes())
    obj['agent_id'] = agent_id
    b.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError):
        run_compare(folder, tmp_path / 'out')


def test_explicit_catalog_and_repeated_positions(capture, tmp_path):
    path, obj = capture
    obj['frames'].append(dict(obj['frames'][0], frame_id='f2'))
    path.write_bytes(ar.encoded(obj))
    catalog = tmp_path / 'catalog.json'
    catalog.write_bytes(ar.CATALOG.read_bytes())
    packet = ar.prepare(path, tmp_path / 'packet', catalog=catalog)
    assert len(packet['frames']) == 2
    assert packet['frames'][0]['captured_at'] == obj['frames'][0]['captured_at']
    assert packet['frames'][0]['video_time_seconds'] == 1
    assert packet['coverage_counts'] == dict(frame_count=2, unique_image_hashes=1,
                                            unique_video_positions=1, unique_image_position_pairs=1)


def test_write_failure_removes_only_new_output(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.write_bytes(b'preserve')
    output = tmp_path / 'output'
    original = type(source).write_bytes

    def fail(path, data):
        if path.name == 'fail.json':
            raise OSError('write failed')
        return original(path, data)

    monkeypatch.setattr(type(source), 'write_bytes', fail)
    with pytest.raises(OSError, match='write failed'):
        ar.publish(output, {'ok.json': b'{}', 'fail.json': b'{}'}, ar.Inputs())
    assert not output.exists()
    assert source.read_bytes() == b'preserve'
    with pytest.raises(ValueError, match='new'):
        ar.publish(tmp_path, {}, ar.Inputs())
    assert source.read_bytes() == b'preserve'


def test_help_without_site_packages():
    import subprocess
    import sys

    result = subprocess.run([sys.executable, '-S', ar.__file__, '--help'],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert 'prepare,compare' in result.stdout


def test_compare_explicit_catalog(capture, tmp_path):
    path, _ = capture
    folder = tmp_path / 'packet'
    catalog = tmp_path / 'catalog.json'
    catalog.write_bytes(ar.CATALOG.read_bytes())
    ar.prepare(path, folder, catalog=catalog)
    submissions(folder)
    report = ar.compare(folder / 'packet.json', folder / 'AI_A.json', folder / 'AI_B.json',
                        tmp_path / 'comparison', catalog=catalog)
    assert report['coverage_counts']['frame_count'] == 1
    assert report['continuous_coverage_verified'] is False


def test_jpeg_wrong_extension_preserved(capture, tmp_path):
    path, obj = capture
    source = tmp_path / 'frame.png'
    Image.new('RGB', (12, 8), 'black').save(source, format='JPEG')
    data = source.read_bytes()
    obj['frames'][0].update(bytes=len(data), sha256=ar.digest(data))
    path.write_bytes(ar.encoded(obj))
    folder = tmp_path / 'packet'
    packet = ar.prepare(path, folder)
    frame = packet['frames'][0]
    assert frame['image_format'] == 'JPEG'
    assert frame['path'] == 'frames/0000.jpg'
    assert (folder / frame['path']).read_bytes() == data
    submissions(folder)
    assert run_compare(folder, tmp_path / 'comparison')['coverage_counts']['frame_count'] == 1


def test_other_image_format_rejected(capture, tmp_path):
    path, obj = capture
    source = tmp_path / 'frame.png'
    Image.new('RGB', (12, 8)).save(source, format='GIF')
    data = source.read_bytes()
    obj['frames'][0].update(bytes=len(data), sha256=ar.digest(data))
    path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError, match='PNG or JPEG signature'):
        ar.prepare(path, tmp_path / 'packet')
    assert not (tmp_path / 'packet').exists()


def test_forged_packet_format_rejected(capture, tmp_path):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    packet_path = folder / 'packet.json'
    obj = json.loads(packet_path.read_bytes())
    obj['frames'][0]['image_format'] = 'JPEG'
    packet_path.write_bytes(ar.encoded(obj))
    submissions(folder)
    for slot in ('A', 'B'):
        review_path = folder / f'AI_{slot}.json'
        obj = json.loads(review_path.read_bytes())
        obj['packet_sha256'] = ar.digest(packet_path.read_bytes())
        review_path.write_bytes(ar.encoded(obj))
    with pytest.raises(ValueError, match='image format mismatch'):
        run_compare(folder, tmp_path / 'out')


@pytest.mark.parametrize('a_clock,b_clock,status', [('9:54', '09:54', 'same'),
                                                   ('9:54.0', '09:54', 'same'),
                                                   ('9:54', '09:44', 'discordant')])
def test_clock_numeric_comparison(capture, tmp_path, a_clock, b_clock, status):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    for slot, clock in (('A', a_clock), ('B', b_clock)):
        p = folder / f'AI_{slot}.json'
        value = json.loads(p.read_bytes())
        value['observations'][0]['clock'] = clock
        p.write_bytes(ar.encoded(value))
    report = run_compare(folder, tmp_path / 'comparison')
    assert report['frames'][0]['fields']['clock'] == dict(a=a_clock, b=b_clock, status=status)
    assert 'clock_comparison_normalization' in report


@pytest.mark.parametrize('clock', ['9:60', '09:99', '999:54', '9:4', '9:54.22'])
def test_invalid_clock_rejected(capture, tmp_path, clock):
    path, _ = capture
    folder = tmp_path / 'packet'
    ar.prepare(path, folder)
    submissions(folder)
    p = folder / 'AI_A.json'
    value = json.loads(p.read_bytes())
    value['observations'][0]['clock'] = clock
    p.write_bytes(ar.encoded(value))
    with pytest.raises(ValueError, match='invalid clock'):
        run_compare(folder, tmp_path / 'comparison')
