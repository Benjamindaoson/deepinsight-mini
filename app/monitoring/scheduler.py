"""APScheduler 3 worker; never started by a FastAPI worker or browser."""

import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import Store, now


def execute_slot(store, kind, at=None, runner=None):
    if kind not in ["morning", "evening"]:
        raise ValueError("Unsupported scheduled briefing")
    from app.skills.monitor import run_monitor

    runner = runner or (lambda s, trigger: run_monitor(s, trigger, force_analysis=s.setting('scheduled_ai_analysis', True)))
    local = (at or datetime.now(timezone.utc)).astimezone(ZoneInfo("Europe/London"))
    slot = f"{local.date()}/{kind}"
    claimed = store.execute("INSERT OR IGNORE INTO schedule_slots VALUES (?,?,NULL,'CLAIMED')", (slot, now()))
    if not claimed:
        return dict(slot=slot, status="ALREADY_CLAIMED", deduplicated=True)
    store.set_setting("scheduler_heartbeat", now())
    try:
        result = runner(store, kind)
        store.execute(
            "UPDATE schedule_slots SET run_id=?,status=? WHERE slot=?", (result["id"], result["status"], slot)
        )
    except Exception as exc:
        result = dict(slot=slot, status="FAILED", error_type=type(exc).__name__)
        store.execute("UPDATE schedule_slots SET status='FAILED' WHERE slot=?", (slot,))
    store.audit(
        "SCHEDULED_BRIEFING",
        slot,
        dict(status=result["status"], run_id=result.get("id"), scheduler="APScheduler 3 or shared OS timer"),
    )
    return result


def build_scheduler(store, blocking=False):
    cls = BlockingScheduler if blocking else BackgroundScheduler
    scheduler = cls(
        timezone=ZoneInfo("Europe/London"),
        job_defaults=dict(coalesce=True, max_instances=1, misfire_grace_time=180),
    )
    for kind, default in [("morning", "08:00"), ("evening", "18:00")]:
        hour, minute = map(int, store.setting(kind + "_time", default).split(":"))
        scheduler.add_job(
            execute_slot,
            CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo("Europe/London")),
            args=[store, kind],
            id="mini-" + kind,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=180,
        )
    return scheduler


def main():
    parser = argparse.ArgumentParser(description="Independent London-time APScheduler worker")
    parser.add_argument(
        "--acceptance-delay",
        type=int,
        help="Explicit controlled date-trigger acceptance, 1..60 seconds; one execution then exit",
    )
    args = parser.parse_args()
    store = Store()
    # The same persistent slot identity also prevents overlap with an OS timer.
    from app.monitoring.worker_lock import worker_lock

    with worker_lock(store):
        scheduler = build_scheduler(store, blocking=True)
        if args.acceptance_delay is not None:
            if not 1 <= args.acceptance_delay <= 60:
                parser.error("Acceptance delay must be 1..60 seconds")
            from datetime import timedelta
            from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

            scheduler.remove_all_jobs()
            scheduler.add_job(
                execute_slot,
                "date",
                run_date=datetime.now(timezone.utc) + timedelta(seconds=args.acceptance_delay),
                args=[store, "morning"],
                id="controlled-real-acceptance",
                max_instances=1,
                misfire_grace_time=180,
            )
            scheduler.add_listener(
                lambda _: scheduler.shutdown(wait=False), EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
        store.set_setting(
            "apscheduler_worker",
            dict(started_at=now(), timezone="Europe/London", pid=__import__("os").getpid()),
        )
        scheduler.start()


if __name__ == "__main__":
    main()
