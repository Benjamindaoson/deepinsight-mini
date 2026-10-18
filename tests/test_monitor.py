from app.database import Store
from app.skills.monitor import run_monitor, review_observation


SOURCE = dict(id="fixture", name="ISOLATED TEST ONLY", url="https://example.org/test",
              type="research", enabled=True, geographies=["City"], observation_period="2026Q2")


def document(text="A public office research document with no quantitative claims."):
    from app.skills.source_reader import digest
    return dict(source_id="fixture", publisher="ISOLATED TEST ONLY", url=SOURCE["url"],
        title="ISOLATED TEST ONLY office research", text=text, hash=digest(text),
        raw_hash=digest(text), raw_path="TEST_ONLY", geography="City",
        published_at="2026-06-30", pages=[], access="TEST ONLY")


def test_baseline_idempotency_and_changed_document(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    def fetch(_):
        return [document()]
    a = run_monitor(s, "test", sources=[SOURCE], reader=fetch, generate=False)
    b = run_monitor(s, "test", sources=[SOURCE], reader=fetch, generate=False)
    c = run_monitor(s, "test", sources=[SOURCE], reader=lambda _: [document("Changed office research body")], generate=False)
    assert a["baseline"] == 1 and a["new_documents"] == 1
    assert a["status"] == b["status"] == c["status"] == "SUCCESS"
    assert b["new_documents"] == 0 and b["new_events"] == 0
    assert c["new_documents"] == 1
    assert s.one("SELECT count(*) n FROM documents")["n"] == 2
    assert s.one("SELECT previous_id FROM documents WHERE version=2")["previous_id"]
    assert s.one("SELECT count(*) n FROM signals WHERE priority!='INFO'")["n"] == 0


def test_failed_source_cannot_be_no_change_success(tmp_path):
    def broken(_):
        raise ValueError("TEST ONLY source unavailable")
    s = Store(tmp_path / "db.sqlite")
    result = run_monitor(s, "test", sources=[SOURCE], reader=broken, generate=False)
    assert result["status"] == "FAILED"
    assert s.one("SELECT status FROM sources")["status"] == "FETCH_FAILED"


def test_review_requires_source_quote_and_reviewer(tmp_path):
    import pytest
    s = Store(tmp_path / "db.sqlite")
    run_monitor(s, "test", sources=[SOURCE], reader=lambda _: [document()], generate=False)
    d = s.one("SELECT id FROM documents")["id"]
    s.execute("INSERT INTO observations(id,document_id,evidence_text,review_status) VALUES (?,?,?,?)",
              ("x", d, "invented quote", "PENDING_REVIEW"))
    with pytest.raises(ValueError):
        review_observation(s, "x", "APPROVED", "Reviewer", "Test")


def test_retracted_observation_invalidates_signal(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO observations(id,review_status) VALUES ('x','RETRACTED')")
    s.execute("INSERT INTO signals(id,observation_id,status) VALUES ('s','x','ACTIVE')")
    s.invalidate()
    assert s.one("SELECT status FROM signals")["status"] == "INVALIDATED"
