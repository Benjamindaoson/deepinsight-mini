from datetime import datetime

from app.database import Store
from app.services.scheduler import due_slots
from app.services.notifications import dispatch
from app.skills.report import make_report


def test_london_schedule_dst():
    assert due_slots(datetime.fromisoformat("2026-07-02T07:00:00+00:00"), {}) == [("2026-07-02/morning", "morning")]
    assert due_slots(datetime.fromisoformat("2026-12-02T08:00:00+00:00"), {}) == [("2026-12-02/morning", "morning")]
    assert due_slots(datetime.fromisoformat("2026-12-02T07:00:00+00:00"), {}) == []


def test_no_approved_numbers_no_charts_and_spool_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("MINI_OUTPUT_DIR", str(tmp_path / "out"))
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO monitor_runs(id,status,started_at,finished_at,trigger) VALUES ('r','FAILED','a','b','test')")
    report = make_report(s, "r")
    assert not report["data"]["charts"]
    assert "Incomplete" in " ".join(report["data"]["executive_summary"])
    assert dispatch(s, report["id"]) == [{"channel": "external", "status": "DISABLED"}]
    s.set_setting("notification_mode", "spool")
    a = dispatch(s, report["id"])
    b = dispatch(s, report["id"])
    assert a[0]["status"] == "CAPTURED_TEST_ONLY"
    assert b[0]["status"] == "DEDUPLICATED"
    assert s.one("SELECT count(*) n FROM notifications")["n"] == 1


def test_untrusted_source_escapes_html(tmp_path, monkeypatch):
    monkeypatch.setenv("MINI_OUTPUT_DIR", str(tmp_path / "out"))
    s = Store(tmp_path / "db.sqlite")
    s.execute("INSERT INTO monitor_runs(id,status,trigger) VALUES ('r','PARTIAL','<script>alert(1)</script>')")
    r = make_report(s, "r")
    assert "<script>alert(1)</script>" not in open(r["html_path"], encoding="utf-8").read()
