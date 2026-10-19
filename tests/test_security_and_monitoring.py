import socket
from datetime import datetime, timezone

import pytest

from app.database import Store
from app.services.scheduler import tick
from app.skills.source_reader import validate_url
from app.skills.monitor import monitor_lock


@pytest.mark.parametrize("url",["http://example.org/a", "https://127.0.0.1/", "https://evil.example/", "https://user:pass@example.org/"])
def test_unregistered_private_or_credentialed_url_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url,{"example.org"})


def test_fakeip_tunnel_exception_does_not_allow_private_addresses(monkeypatch):
    monkeypatch.setenv("MINI_TUNNEL_DNS","1")
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**kw:[(2,1,0,"",("127.0.0.1",443))])
    with pytest.raises(ValueError):
        validate_url("https://example.org/",{"example.org"})


def test_process_lock_rejects_overlapping_monitor(tmp_path):
    store=Store(tmp_path/"db.sqlite")
    with monitor_lock(store):
        with pytest.raises(RuntimeError,match="already running"):
            with monitor_lock(store):
                pass


def test_schedule_slot_claim_is_durable(tmp_path,monkeypatch):
    store=Store(tmp_path/"db.sqlite")
    calls=[]
    def run(s,trigger,*,force_analysis=False):
        calls.append(trigger)
        return {"id":"isolated-test-only", "status":"SUCCESS"}
    monkeypatch.setattr("app.skills.monitor.run_monitor",run)
    at=datetime(2026,12,2,8,0,tzinfo=timezone.utc)
    assert len(tick(store,at))==1
    assert tick(Store(store.path),at)==[]
    assert calls==["morning"]
