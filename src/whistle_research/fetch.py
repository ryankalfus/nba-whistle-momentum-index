"""Explicit, verified acquisition of immutable manifest inputs without replacement."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from whistle_research.sources import safe_path

CHUNK_BYTES = 1024 * 1024


def https_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("source URL must use HTTPS")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment):
        raise ValueError("source URL must use HTTPS without credentials or fragments")
    return value


class HTTPSOnlyRedirect(HTTPRedirectHandler):
    """Reject a redirect downgrade before urllib sends the redirected request."""

    def redirect_request(self, request, response, code, message, headers, newurl):
        https_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def open_https(url: str):
    return build_opener(HTTPSOnlyRedirect()).open(https_url(url), timeout=60)


def reject_constant(value):
    raise ValueError(f"nonstandard JSON constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def no_symlinks(root: Path, target: Path) -> None:
    for component in (target, *target.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("source path contains a symlink")


def bounded_digest(stream, expected_bytes: int, destination=None) -> tuple[int, str]:
    """Read at most the declared size plus one byte, including unknown-length bodies."""
    digest, count = hashlib.sha256(), 0
    while True:
        chunk = stream.read(min(CHUNK_BYTES, expected_bytes - count + 1))
        if not chunk:
            break
        count += len(chunk)
        if count > expected_bytes:
            raise ValueError("body exceeds declared bytes")
        digest.update(chunk)
        if destination is not None:
            destination.write(chunk)
    return count, digest.hexdigest()


def acquire_one(entry: dict, cache: Path) -> dict:
    row = {"source_file": entry["file"], "source_url": entry["url"],
           "expected_bytes": entry["bytes"], "expected_sha256": entry["sha256"]}
    temporary = None
    try:
        target = safe_path(cache, entry["file"])
        no_symlinks(cache, target)
        expected = (entry["bytes"], entry["sha256"])
        if target.exists():
            if not target.is_file():
                raise ValueError("existing source is not a regular file")
            with target.open("rb") as stream:
                observed = bounded_digest(stream, entry["bytes"])
            row.update(actual_bytes=observed[0], actual_sha256=observed[1])
            if observed != expected:
                raise ValueError("existing cache does not match declared bytes and SHA256")
            row["status"] = "cached_verified"
            return row
        target.parent.mkdir(parents=True, exist_ok=True)
        no_symlinks(cache, target)
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".fetch-", dir=target.parent,
                                         delete=False) as destination:
            temporary = Path(destination.name)
            with open_https(entry["url"]) as response:
                https_url(response.geturl())
                observed = bounded_digest(response, entry["bytes"], destination)
            destination.flush()
            os.fsync(destination.fileno())
        row.update(actual_bytes=observed[0], actual_sha256=observed[1])
        if observed != expected:
            raise ValueError("download does not match declared bytes and SHA256")
        no_symlinks(cache, target)
        # link() is an atomic exclusive publication: a concurrent creator wins.
        os.link(temporary, target)
        row["status"] = "downloaded_verified"
    except (OSError, ValueError, URLError, HTTPException) as exc:
        row.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return row


def acquire(manifest: Path, cache: Path) -> dict:
    """Validate the entire declaration before any network request or cache write."""
    raw = manifest.read_bytes()
    entries = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(entries, list) or not entries:
        raise ValueError("source manifest must be a nonempty list")
    names = [entry.get("file") for entry in entries if isinstance(entry, dict)]
    duplicates = {name for name, count in Counter(n for n in names if isinstance(n, str)).items() if count > 1}
    cache = cache.absolute()
    rows = []
    for index, entry in enumerate(entries):
        row = {"manifest_index": index, "status": "pending"}
        try:
            if not isinstance(entry, dict):
                raise ValueError("source entry must be an object")
            name = entry.get("file")
            row["source_file"] = name
            target = safe_path(cache, name)
            no_symlinks(cache, target)
            if name in duplicates:
                raise ValueError("duplicate source path")
            if any(isinstance(other, str) and other.startswith(name + "/") for other in names):
                raise ValueError("source paths conflict as file and directory")
            size, sha = entry.get("bytes"), entry.get("sha256")
            if type(size) is not int or size < 0 or not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
                raise ValueError("expected nonnegative bytes and lowercase SHA256")
            https_url(entry.get("url"))
        except (ValueError, OSError, TypeError) as exc:
            row.update(status="invalid_manifest", reason=str(exc))
        rows.append(row)
    if any(row["status"] == "invalid_manifest" for row in rows):
        for row in rows:
            if row["status"] == "pending":
                row["status"] = "blocked_invalid_manifest"
    else:
        rows = [{"manifest_index": index, **acquire_one(entry, cache)}
                for index, entry in enumerate(entries)]
    return {"schema_version": "source-fetch-v1", "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "sources": rows, "ok": all(row["status"] in {"cached_verified", "downloaded_verified"} for row in rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    # Reserve the report destination before any acquisition; never replace an old run.
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = acquire(args.manifest, args.cache)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result = {"schema_version": "source-fetch-v1", "ok": False, "sources": [],
                  "reason": f"{type(exc).__name__}: {exc}"}
    with (args.output / "fetch.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
