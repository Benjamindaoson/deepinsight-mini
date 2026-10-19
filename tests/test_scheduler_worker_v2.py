from datetime import datetime, timezone
from app.database import Store


def test_worker_has_london_cron_jobs_and_no_web_scheduler(tmp_path):
    from app.monitoring.scheduler import build_scheduler

    store = Store(tmp_path / "db.sqlite3")
    scheduler = build_scheduler(store)
    assert str(scheduler.timezone) == "Europe/London"
    jobs = scheduler.get_jobs()
    assert {j.id for j in jobs} == {"mini-morning", "mini-evening"}
    assert all(j.max_instances == 1 and j.coalesce for j in jobs)
    assert "hour='8'" in str(next(j.trigger for j in jobs if j.id == "mini-morning"))


def test_persisted_slot_claim_survives_restart_without_duplicate_runner(tmp_path):
    from app.monitoring.scheduler import execute_slot

    store = Store(tmp_path / "db.sqlite3")
    calls = []

    def run(s, kind):
        calls.append(kind)
        return {"id": "SYNTHETIC-run", "status": "SUCCESS"}

    at = datetime(2026, 7, 2, 7, 0, tzinfo=timezone.utc)
    first = execute_slot(store, "morning", at, runner=run)
    again = execute_slot(Store(store.path), "morning", at, runner=run)
    assert first["id"] == "SYNTHETIC-run" and again["deduplicated"] and calls == ["morning"]
    assert store.one("SELECT status FROM schedule_slots")["status"] == "SUCCESS"


def test_worker_failure_is_retained_without_blind_retry(tmp_path):
    from app.monitoring.scheduler import execute_slot

    store = Store(tmp_path / "db.sqlite3")
    calls = []

    def fail(s, kind):
        calls.append(kind)
        raise RuntimeError("private payload")

    at = datetime(2026, 7, 2, 7, 0, tzinfo=timezone.utc)
    result = execute_slot(store, "morning", at, runner=fail)
    assert result["status"] == "FAILED" and "private" not in str(result)
    assert execute_slot(store, "morning", at, runner=fail)["deduplicated"] and len(calls) == 1
