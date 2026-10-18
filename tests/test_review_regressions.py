from app.database import Store
from app.agent import validate_answer
from app.skills.monitor import save_document
from tests.test_monitor import SOURCE, document
from app.skills.report import make_report, rendered_report


def test_unrelated_approved_observation_cannot_authorize_pending_number(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO sources(id,status) VALUES ('s','HEALTHY')")
    text = "Rent is 100 pounds. Vacancy is 9.9%."
    s.execute("INSERT INTO documents(id,source_id,text,status) VALUES ('d','s',?,'SOURCE_VERIFIED')", (text,))
    s.execute("INSERT INTO observations(id,document_id,value,evidence_text,review_status) VALUES ('rent','d',100,'Rent is 100 pounds.','APPROVED')")
    result = validate_answer(s, {"summary":"Draft", "claims":[{"text":"Vacancy is 9.9%.","quote":"Vacancy is 9.9%.","document_id":"d","kind":"fact","observation_id":"rent"}]})
    assert result["claims"] == []


def test_body_reversion_restores_current_evidence_without_duplicate_body(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO sources(id,status) VALUES ('fixture','HEALTHY')")
    a = save_document(s, document("Original public office body"), SOURCE)
    b = save_document(s, document("Revised public office body"), SOURCE)
    restored = save_document(s, document("Original public office body"), SOURCE)
    assert restored == a
    assert s.one("SELECT status FROM documents WHERE id=?", (a,))["status"] == "SOURCE_VERIFIED"
    assert s.one("SELECT status FROM documents WHERE id=?", (b,))["status"] == "SUPERSEDED"
    assert s.one("SELECT count(*) n FROM documents")["n"] == 2


def test_superseded_previous_observation_invalidates_delta(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO sources(id,status) VALUES ('s','HEALTHY')")
    for ident, status in [('old','SUPERSEDED'),('new','SOURCE_VERIFIED')]:
        s.execute("INSERT INTO documents(id,source_id,status) VALUES (?,'s',?)", (ident,status))
        s.execute("INSERT INTO observations(id,document_id,review_status) VALUES (?,?,'APPROVED')", (ident,ident))
    s.execute("INSERT INTO signals(id,document_id,observation_id,previous_observation_id,status) VALUES ('sig','new','new','old','ACTIVE')")
    s.invalidate()
    assert s.one("SELECT status FROM signals")["status"] == "INVALIDATED"


def test_model_limitations_cannot_smuggle_market_claims(tmp_path):
    result = validate_answer(Store(tmp_path / "db.sqlite"), {"summary":"Draft", "claims":[], "limitations":["City vacancy is 99%."]})
    assert "99%" not in str(result)


def test_report_retraction_warning_applies_to_shared_html(tmp_path, monkeypatch):
    monkeypatch.setenv("MINI_OUTPUT_DIR", str(tmp_path / "out"))
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO sources(id,status) VALUES ('s','HEALTHY')")
    s.execute("INSERT INTO documents(id,source_id,status) VALUES ('d','s','SOURCE_VERIFIED')")
    s.execute("INSERT INTO observations(id,document_id,metric,value,review_status) VALUES ('o','d','prime_rent',100,'APPROVED')")
    result = make_report(s)
    s.execute("UPDATE observations SET review_status='RETRACTED' WHERE id='o'")
    row = s.one("SELECT * FROM reports WHERE id=?", (result["id"],))
    html = rendered_report(s, row)
    assert "Historical briefing" in html


def test_channel_test_receipt_does_not_authorize_failed_channel(tmp_path, monkeypatch):
    from app.services.notifications import dispatch
    monkeypatch.setenv("MINI_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.delenv("MINI_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("MINI_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr("app.services.notifications.send_email", lambda *a, **kw: "ISOLATED STUB ONLY")
    s = Store(tmp_path / "db.sqlite")
    report = make_report(s)
    s.set_setting("notification_mode", "enabled")
    s.set_setting("email_recipient", "test@example.invalid")
    s.set_setting("telegram_enabled", True)
    test_results = dispatch(s, report["id"], test=True)
    assert test_results[0]["status"] == "ACCEPTED"
    assert test_results[1]["status"] == "FAILED_REVIEW_REQUIRED"
    actual = dispatch(s, report["id"])
    assert actual[1]["status"] == "BLOCKED_TEST_REQUIRED"
    monkeypatch.setenv("MINI_SMTP_PORT", "9999")
    assert dispatch(s, make_report(s)["id"])[0]["status"] == "BLOCKED_TEST_REQUIRED"
