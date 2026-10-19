def get_monitor_status(store, args):
    from app.services.scheduler import next_slots

    return dict(
        last_run=store.one("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1"),
        next_runs=next_slots(store),
        heartbeat=store.setting("scheduler_heartbeat"),
        sources=store.query("SELECT id,name,status,last_success,error FROM sources"),
        evidence_ids=[],
    )


def get_verified_changes(store, args):
    from app.analytics.publication import verified_metric_signals

    rows = verified_metric_signals(store)[:50]
    return dict(
        signals=rows, evidence_ids=list(dict.fromkeys(r["document_id"] for r in rows if r.get("document_id")))
    )


def run_market_monitor(store, args):
    from app.skills.monitor import run_monitor

    result = run_monitor(store, "explicit_tool_request")
    return dict(
        run=result,
        evidence_ids=[],
        warnings=["A completed collection does not imply approved observations or successful AI."],
    )
