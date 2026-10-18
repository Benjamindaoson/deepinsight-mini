"""Independent durable London-time slots; called by OS timer, not the web server."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.database import now


def due_slots(at, settings):
    local = at.astimezone(ZoneInfo("Europe/London"))
    slots = []
    for kind, default in (("morning", "08:00"), ("evening", "18:00")):
        target = settings.get(kind + "_time", default)
        hour, minute = map(int, target.split(":"))
        if (local.hour, local.minute) == (hour, minute):
            slots.append((f"{local.date()}/{kind}", kind))
    return slots


def tick(store, at=None):
    from app.skills.monitor import run_monitor
    at = at or datetime.now(timezone.utc)
    store.set_setting("scheduler_heartbeat", now())
    settings = {k: store.setting(k, default) for k, default in (("morning_time", "08:00"), ("evening_time", "18:00"))}
    results = []
    for slot, kind in due_slots(at, settings):
        claimed = store.execute("INSERT OR IGNORE INTO schedule_slots VALUES (?,?,NULL,'CLAIMED')", (slot, now()))
        if not claimed:
            continue
        try:
            result = run_monitor(store, kind)
            store.execute("UPDATE schedule_slots SET run_id=?,status=? WHERE slot=?", (result["id"], result["status"], slot))
            results.append(result)
        except Exception as exc:
            store.execute("UPDATE schedule_slots SET status=? WHERE slot=?", ("FAILED_" + type(exc).__name__, slot))
            results.append({"slot": slot, "status": "FAILED", "error": type(exc).__name__})
    store.audit("SCHEDULER_TICK", at.isoformat(), {"slots": [r.get("id", r.get("slot")) for r in results]})
    return results


def next_slots(store, at=None):
    from datetime import timedelta
    local = (at or datetime.now(timezone.utc)).astimezone(ZoneInfo("Europe/London"))
    result = []
    for kind, default in (("morning", "08:00"), ("evening", "18:00")):
        time = store.setting(kind + "_time", default)
        h, m = map(int, time.split(":"))
        target = local.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= local:
            target = (local + timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
        result.append({"type": kind, "at": target.isoformat(), "timezone": "Europe/London"})
    return result
