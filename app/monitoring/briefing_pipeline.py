"""Existing collector→detector→agent→report→outbox transaction sequence."""

from app.skills.monitor import run_monitor


def run_briefing(store, kind):
    return run_monitor(store, kind)
