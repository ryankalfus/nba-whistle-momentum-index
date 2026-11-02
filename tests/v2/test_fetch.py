"""Offline acquisition contracts: verified bytes or explicit failure, never replace."""

import hashlib
from http.client import IncompleteRead
import io
import json
from urllib.error import URLError

import pytest

from whistle_research import fetch


class Response(io.BytesIO):
    def geturl(self):
        return "https://example.test/pinned/source"


def fixture_manifest(tmp_path, payload=b"immutable source", **changes):
    entry = {"file": "nested/source.bin", "url": "https://example.test/pinned/source",
             "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), **changes}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([entry]))
    return manifest, tmp_path / "cache", entry, payload


def serve(monkeypatch, payload):
    calls = []

    def request(url):
        calls.append(url)
        return Response(payload)

    monkeypatch.setattr(fetch, "open_https", request)
    return calls


def test_verified_download_cached_reuse_and_manifest_unchanged(tmp_path, monkeypatch):
    manifest, cache, entry, payload = fixture_manifest(tmp_path)
    original = manifest.read_bytes()
    calls = serve(monkeypatch, payload)
    assert fetch.main(["--manifest", str(manifest), "--cache", str(cache),
                       "--output", str(tmp_path / "report")]) == 0
    report = json.loads((tmp_path / "report/fetch.json").read_text())
    assert report["sources"][0]["status"] == "downloaded_verified"
    target = cache / entry["file"]
    assert target.read_bytes() == payload
    before = target.stat().st_mtime_ns
    assert fetch.acquire(manifest, cache)["sources"][0]["status"] == "cached_verified"
    assert target.stat().st_mtime_ns == before
    assert calls == [entry["url"]]
    assert manifest.read_bytes() == original
    assert not list(cache.rglob(".fetch-*"))


@pytest.mark.parametrize("payload", [b"wrong same size!", b"short", b"immutable source-extra"])
def test_wrong_download_not_published_and_temporary_cleaned(tmp_path, monkeypatch, payload):
    manifest, cache, entry, _ = fixture_manifest(tmp_path)
    serve(monkeypatch, payload)
    result = fetch.acquire(manifest, cache)
    assert not result["ok"]
    assert result["sources"][0]["status"] == "failed"
    assert not (cache / entry["file"]).exists()
    assert not list(cache.rglob(".fetch-*"))


def test_oversize_response_read_is_bounded(tmp_path, monkeypatch):
    manifest, cache, _, _ = fixture_manifest(tmp_path, payload=b"abc")
    sizes = []

    class LargeResponse(Response):
        def read(self, size=-1):
            sizes.append(size)
            assert size > 0
            return super().read(size)

    monkeypatch.setattr(fetch, "open_https", lambda url: LargeResponse(b"x" * 1000))
    assert not fetch.acquire(manifest, cache)["ok"]
    assert sizes == [4]


def test_download_error_is_reported_and_cleaned(tmp_path, monkeypatch):
    manifest, cache, entry, _ = fixture_manifest(tmp_path)

    def fail(url):
        raise URLError("offline fixture failure")

    monkeypatch.setattr(fetch, "open_https", fail)
    output = tmp_path / "failed-report"
    assert fetch.main(["--manifest", str(manifest), "--cache", str(cache),
                       "--output", str(output)]) == 1
    report = json.loads((output / "fetch.json").read_text())
    assert "offline fixture failure" in report["sources"][0]["reason"]
    assert not (cache / entry["file"]).exists()
    assert not list(cache.rglob(".fetch-*"))


@pytest.mark.parametrize("existing", [b"bad", b"x" * 1000])
def test_existing_mismatch_refused_without_request_or_overwrite(tmp_path, monkeypatch, existing):
    manifest, cache, entry, payload = fixture_manifest(tmp_path)
    target = cache / entry["file"]
    target.parent.mkdir(parents=True)
    target.write_bytes(existing)
    calls = serve(monkeypatch, payload)
    assert not fetch.acquire(manifest, cache)["ok"]
    assert target.read_bytes() == existing
    assert calls == []


def test_concurrent_existing_file_wins_exclusive_publish(tmp_path, monkeypatch):
    manifest, cache, entry, payload = fixture_manifest(tmp_path)
    serve(monkeypatch, payload)
    original_link = fetch.os.link

    def competing_link(source, target):
        target.write_bytes(b"concurrent owner")
        original_link(source, target)

    monkeypatch.setattr(fetch.os, "link", competing_link)
    assert not fetch.acquire(manifest, cache)["ok"]
    assert (cache / entry["file"]).read_bytes() == b"concurrent owner"
    assert not list(cache.rglob(".fetch-*"))


@pytest.mark.parametrize("changes", [
    {"url": None}, {"url": "http://example.test/source"},
    {"url": "file:///source"}, {"url": "https://user:pass@example.test/source"},
    {"file": "../escape"}, {"file": "/absolute"}, {"file": "a/../b"},
    {"file": "a\\b"}, {"sha256": "bad"}, {"bytes": -1}, {"bytes": True},
])
def test_invalid_manifest_never_requests_or_writes(tmp_path, monkeypatch, changes):
    manifest, cache, _, payload = fixture_manifest(tmp_path, **changes)
    calls = serve(monkeypatch, payload)
    result = fetch.acquire(manifest, cache)
    assert not result["ok"]
    assert result["sources"][0]["status"] == "invalid_manifest"
    assert not cache.exists()
    assert calls == []


def test_missing_url_and_duplicate_paths_block_entire_manifest(tmp_path, monkeypatch):
    manifest, cache, entry, payload = fixture_manifest(tmp_path)
    calls = serve(monkeypatch, payload)
    no_url = {key: value for key, value in entry.items() if key != "url"}
    for entries in ([no_url], [entry, entry], [entry, {**entry, "file": "other", "url": None}]):
        manifest.write_text(json.dumps(entries))
        result = fetch.acquire(manifest, cache)
        assert not result["ok"]
        assert all(row["status"] in {"invalid_manifest", "blocked_invalid_manifest"}
                   for row in result["sources"])
    assert not cache.exists()
    assert calls == []


def test_duplicate_json_key_and_empty_manifest_report_failure(tmp_path, monkeypatch):
    manifest, cache, _, payload = fixture_manifest(tmp_path)
    calls = serve(monkeypatch, payload)
    for index, text in enumerate(('[{"file":"a","file":"b"}]', '[]', '{}', '[{"file":NaN}]')):
        manifest.write_text(text)
        output = tmp_path / f"invalid-{index}"
        assert fetch.main(["--manifest", str(manifest), "--cache", str(cache),
                           "--output", str(output)]) == 1
        assert not json.loads((output / "fetch.json").read_text())["ok"]
    assert calls == []


def test_existing_report_refused_before_network(tmp_path, monkeypatch):
    manifest, cache, _, payload = fixture_manifest(tmp_path)
    calls = serve(monkeypatch, payload)
    output = tmp_path / "existing"
    output.mkdir()
    (output / "fetch.json").write_text("preserved")
    with pytest.raises(FileExistsError):
        fetch.main(["--manifest", str(manifest), "--cache", str(cache), "--output", str(output)])
    assert (output / "fetch.json").read_text() == "preserved"
    assert calls == []


def test_symlink_and_file_directory_collisions_rejected(tmp_path, monkeypatch):
    manifest, cache, entry, payload = fixture_manifest(tmp_path)
    calls = serve(monkeypatch, payload)
    cache.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (cache / "nested").symlink_to(outside, target_is_directory=True)
    assert not fetch.acquire(manifest, cache)["ok"]
    (cache / "nested").unlink()
    manifest.write_text(json.dumps([entry, {**entry, "file": "nested"}]))
    assert not fetch.acquire(manifest, cache)["ok"]
    assert calls == []
    assert not list(outside.iterdir())


def test_redirect_downgrade_rejected_before_following():
    with pytest.raises(ValueError, match="HTTPS"):
        fetch.HTTPSOnlyRedirect().redirect_request(None, None, 302, "Found", {}, "http://example.test/source")


def test_interrupted_body_failure_is_reported(tmp_path, monkeypatch):
    manifest, cache, entry, _ = fixture_manifest(tmp_path)

    class InterruptedResponse(Response):
        def read(self, size=-1):
            raise IncompleteRead(b"partial", 100)

    monkeypatch.setattr(fetch, "open_https", lambda url: InterruptedResponse(b""))
    report = fetch.acquire(manifest, cache)
    assert not report["ok"]
    assert "IncompleteRead" in report["sources"][0]["reason"]
    assert not (cache / entry["file"]).exists()
    assert not list(cache.rglob(".fetch-*"))


def test_empty_declared_source_can_be_verified(tmp_path, monkeypatch):
    manifest, cache, entry, _ = fixture_manifest(tmp_path, payload=b"")
    serve(monkeypatch, b"")
    assert fetch.acquire(manifest, cache)["ok"]
    assert (cache / entry["file"]).read_bytes() == b""
