"""Offline HTTP cache behavior; real collector acceptance is recorded separately."""

import hashlib
from app.skills import source_reader as reader


def test_conditional_http_304_reuses_only_matching_original(tmp_path, monkeypatch):
    source = dict(
        id="cache-test",
        name="SYNTHETIC source",
        url="https://example.org/data",
        collection_method="json",
        frequency="monthly",
    )
    body = b'{"description":{"title":"SYNTHETIC CPI"},"months":[{"date":"2026 JAN","value":"2.0"}]}'
    calls = []
    monkeypatch.setattr(reader, "registry", lambda: [source])
    monkeypatch.setattr(reader, "check_robots", lambda *args: "test policy")

    def fetch(url, hosts, timeout=25, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            kwargs.get("receipt", {}).update(
                status=200, etag='"v1"', last_modified="Wed, 05 Aug 2026 09:00:00 GMT"
            )
            return body, url, "application/json"
        assert kwargs["conditional_headers"]["If-None-Match"] == '"v1"'
        kwargs["receipt"].update(status=304)
        return b"", url, "application/json"

    monkeypatch.setattr(reader, "download", fetch)
    first = reader.read_source(source, tmp_path)[0]
    second = reader.read_source(source, tmp_path)[0]
    assert len(calls) == 2 and first["raw_hash"] == second["raw_hash"] == hashlib.sha256(body).hexdigest()
    assert second["http_status"] == 304 and second["http_cache_status"] == "VERIFIED_ORIGINAL_REUSED"
