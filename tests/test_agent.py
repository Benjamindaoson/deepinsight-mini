import pytest

from app.database import Store
from app.agent import reserve_call, validate_answer, execute_tool, ask


def test_transactional_daily_request_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("MINI_DAILY_REQUESTS", "1")
    s = Store(tmp_path / "db.sqlite")
    reserve_call(s, 100)
    with pytest.raises(ValueError, match="budget"):
        reserve_call(s, 100)


def test_agent_cannot_approve_or_fetch_arbitrary_url(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    with pytest.raises(ValueError):
        execute_tool(s, "approve_fact", {"id": "anything"})
    with pytest.raises(ValueError):
        execute_tool(s, "source_reader", {"document_id": "http://127.0.0.1"})


def test_claim_quote_must_match_and_numbers_require_approval(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO sources(id,status) VALUES ('s','HEALTHY')")
    s.execute("INSERT INTO documents(id,source_id,text,status) VALUES ('d','s','A new office was approved.','SOURCE_VERIFIED')")
    good = {"summary": "A planning update is available.", "claims": [{"text": "A new office was approved.",
            "document_id": "d", "quote": "A new office was approved.", "kind": "fact"}],
            "limitations": ["No approved quantitative observations."]}
    assert validate_answer(s, good)["claims"]
    bad = good | {"claims": [good["claims"][0] | {"text": "Rent rose 12%."}]}
    assert not validate_answer(s, bad)["claims"]
    fabricated = good | {"claims": [good["claims"][0] | {"quote": "Invented evidence."}]}
    assert not validate_answer(s, fabricated)["claims"]


def test_blocked_model_retains_conversation_and_no_fake_ai(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.set_setting("model_block", {"reason": "Provider HTTP 402", "fingerprint": "test"})
    # Explicitly absent credential tests the fail-closed path without network.
    import os
    previous = os.environ.get("MINI_API_KEY")
    os.environ["MINI_API_KEY"] = ""
    try:
        result = ask(s, "What changed?")
    finally:
        if previous is None:
            os.environ.pop("MINI_API_KEY", None)
        else:
            os.environ["MINI_API_KEY"] = previous
    assert result["status"] == "BLOCKED"
    assert "AI" in result["message"]
    assert s.one("SELECT id FROM conversations")
