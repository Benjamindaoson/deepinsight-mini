import pytest
from app.database import Store
from app.analytics.context import resolve_context, MarketContext


def test_bi_scope_inherits_and_explicit_geography_period_change_wins(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    first = resolve_context(
        store,
        "Analyse selected market",
        "c",
        {"geography": "City", "metric": "vacancy_rate", "period": "2026Q2"},
    )
    assert first["geography"] == "City"
    assert resolve_context(store, "Why does it matter?", "c")["period"] == "2026Q2"
    changed = resolve_context(store, "What about Canary Wharf in Q1 2026?", "c")
    assert changed["geography"] == "Canary Wharf" and changed["period"] == "2026Q1"


def test_unknown_evidence_and_raw_sql_context_cannot_gain_authority(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    with pytest.raises(ValueError):
        resolve_context(store, "Analyse market", "c", {"evidence_ids": ["invented"]})
    with pytest.raises(ValueError):
        MarketContext(metric="DROP TABLE observations")


def test_ask_endpoint_passes_typed_dashboard_scope_to_agent(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    import app.agent
    import re
    import threading

    received = {}
    called = threading.Event()

    def capture(*args, **kwargs):
        received.update(kwargs)
        called.set()
        return {
            "status": "BLOCKED",
            "conversation_id": "synthetic",
            "market_context": kwargs.get("market_context"),
        }

    monkeypatch.setattr(app.agent, "ask", capture)
    client = TestClient(create_app(Store(tmp_path / "db.sqlite3")), base_url="http://localhost")
    token = re.search(r'name="csrf-token" content="([^"]+)"', client.get("/").text)[1]
    response = client.post(
        "/api/agent/ask",
        json={
            "question": "Analyse selected evidence",
            "market_context": {"geography": "City", "metric": "vacancy_rate", "period": "2026Q2"},
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert called.wait(2) and received["market_context"]["geography"] == "City"
