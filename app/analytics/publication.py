"""The shared approved evidence boundary for monitoring and report delivery."""

from app.analytics.engine import Analytics, METRICS, QuerySpec


def approved_observations(store):
    engine = Analytics(store)
    # Retain the latest 24 observations of each compatible series, with a hard
    # internal 10,000-row cap per metric. Public tool limits stay at 240.
    return [
        row
        for metric in METRICS
        for row in engine.query(
            QuerySpec(metric=metric, review_status="APPROVED", operation="trend", limit=240), publication=True
        )["rows"]
    ]


def verified_metric_signals(store, observations=None):
    store.invalidate()
    eligible = {
        row["id"]: row for row in (approved_observations(store) if observations is None else observations)
    }
    result = []
    for signal in store.query(
        "SELECT * FROM signals WHERE status='ACTIVE' AND kind='METRIC_CHANGE' ORDER BY created_at DESC"
    ):
        current = eligible.get(signal["observation_id"])
        if not current:
            # A display history limit must never decide signal validity.
            rows = Analytics(store).query(QuerySpec(), observation_ids=[signal["observation_id"]])["rows"]
            current = next((row for row in rows if row["id"] == signal["observation_id"]), None)
        if (
            not current
            or current["comparison_status"] != "COMPARABLE"
            or current["previous_observation_id"] != signal["previous_observation_id"]
            or current["document_id"] != signal["document_id"]
        ):
            store.execute("UPDATE signals SET status='INVALIDATED' WHERE id=?", (signal["id"],))
            continue
        result.append(signal)
    return result
