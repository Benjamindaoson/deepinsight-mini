"""V2 dashboard contracts over the same SQL engine used by domain tools."""

import json
from fastapi import HTTPException, Request
from pydantic import ValidationError
from app.analytics.engine import Analytics, QuerySpec, METRICS

GEOGRAPHIES = ["City", "West End", "Canary Wharf", "Midtown", "Fringe", "Central London", "City Fringe", "UK"]


def parse_filters(request):
    q = request.query_params
    if set(q) - {
        "metric",
        "geography",
        "source",
        "grade",
        "status",
        "review_status",
        "start_period",
        "end_period",
        "time_range",
    }:
        raise HTTPException(400, "Unknown analytical filter. Raw SQL is not accepted.")
    values = dict(
        metric=q.get("metric") or None,
        geographies=[q["geography"]] if q.get("geography") else [],
        source_id=q.get("source") or None,
        grade=q.get("grade", "all"),
        review_status=q.get("status", q.get("review_status", "APPROVED")),
        start_period=q.get("start_period") or None,
        end_period=q.get("end_period") or None,
    )
    try:
        return QuerySpec.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(422, detail=exc.errors(include_context=False)) from None


def dashboard_payload(store, spec, time_range="all"):
    engine = Analytics(store)
    if time_range not in ["all", "last_8_quarters", "last_12_months", "last_24_months", "custom"]:
        raise HTTPException(422, "Unknown time range")
    if time_range.startswith("last_") and not spec.start_period:
        anchor = engine.query(spec.model_copy(update={"operation": "latest", "review_status": "ALL"}))["rows"]
        quarters = [r["period"] for r in anchor if r["frequency"] == "Q"]
        months = [r["period"] for r in anchor if r["frequency"] == "M"]
        if time_range == "last_8_quarters" and quarters:
            end = max(quarters)
            index = int(end[:4]) * 4 + int(end[-1]) - 1
            start = index - 7
            spec = spec.model_copy(
                update={"start_period": f"{start // 4}Q{start % 4 + 1}", "end_period": end}
            )
        elif months:
            end = max(months)
            index = int(end[:4]) * 12 + int(end[-2:]) - 1
            start = index - (11 if time_range == "last_12_months" else 23)
            spec = spec.model_copy(
                update={"start_period": f"{start // 12}M{start % 12 + 1:02}", "end_period": end}
            )
    data = engine.query(spec.model_copy(update={"operation": "trend"}))
    latest = engine.query(spec.model_copy(update={"operation": "latest"}))
    comparison = engine.query(spec.model_copy(update={"operation": "rank", "review_status": "APPROVED"}))
    coverage = engine.query(spec.model_copy(update={"operation": "coverage", "review_status": "ALL"}))
    matrix = []
    for geo in spec.geographies or GEOGRAPHIES:
        for metric in [spec.metric] if spec.metric else METRICS:
            cells = [r for r in coverage["rows"] if r["geography"] == geo and r["metric"] == metric]
            approved = sum(r["observation_count"] for r in cells if r["review_status"] == "APPROVED")
            pending = sum(r["observation_count"] for r in cells if r["review_status"] == "PENDING_REVIEW")
            conflicts = [c for c in data["conflicts"] if c["geography"] == geo and c["metric"] == metric]
            matrix.append(
                dict(
                    geography=geo,
                    metric=metric,
                    status="NOT_COMPARABLE"
                    if conflicts
                    else "VERIFIED"
                    if approved
                    else "PENDING_REVIEW"
                    if pending
                    else "MISSING",
                    approved=approved,
                    pending=pending,
                )
            )
    from app.skills.event_intelligence import get_market_events, EventInput

    events = get_market_events(store, EventInput(geography=spec.geographies[0] if spec.geographies else ""))[
        "events"
    ]
    return dict(
        filters=spec.model_dump(),
        time_range=time_range,
        range_basis="Latest saved observation; not current publication or calendar coverage.",
        observations=data["rows"],
        kpis=latest["rows"],
        submarkets=comparison["rows"],
        coverage=matrix,
        events=events,
        integrity_failures=data["integrity_failures"],
        conflicts=data["conflicts"],
        limitations=data.get("limitations", []),
        sources=store.query("SELECT id,name,status,last_success,error FROM sources"),
        last_monitor=store.one("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1"),
        choices=dict(metrics=list(METRICS), geographies=GEOGRAPHIES),
        review_notice="Pending inspection mode is not approved analysis."
        if spec.review_status != "APPROVED"
        else "Confirmed charts require approved, compatible and original-hash-verified observations.",
    )


def register_bi_routes(web, store):
    @web.get("/api/analytics")
    def analytics(request: Request):
        try:
            return Analytics(store).query(parse_filters(request))
        except HTTPException as exc:
            raise HTTPException(
                400, "Invalid analytical filter. Use a supported indicator, period and review state."
            ) from exc

    def overview(request: Request):
        return dashboard_payload(store, parse_filters(request), request.query_params.get("time_range", "all"))

    web.add_api_route("/api/dashboard/overview", overview, methods=["GET"])
    for name, key in [
        ("kpis", "kpis"),
        ("trends", "observations"),
        ("submarkets", "submarkets"),
        ("coverage", "coverage"),
        ("events", "events"),
    ]:

        def make_endpoint(field):
            def endpoint(request: Request):
                result = overview(request)
                return dict(
                    items=result[field],
                    filters=result["filters"],
                    review_notice=result["review_notice"],
                    integrity_failures=result["integrity_failures"],
                )

            return endpoint

        web.add_api_route("/api/dashboard/" + name, make_endpoint(key), methods=["GET"])

    @web.get("/api/monitor/status")
    def monitor_status():
        from app.skills.continuous_monitoring import get_monitor_status

        return get_monitor_status(store, None)

    @web.get("/api/monitor/runs")
    def monitor_runs():
        return dict(items=store.query("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 100"))

    @web.get("/api/monitor/signals")
    def monitor_signals():
        from app.skills.continuous_monitoring import get_verified_changes

        return get_verified_changes(store, None)

    @web.get("/api/agent/conversations/{identity}")
    def conversation(identity: str, request: Request):
        row = store.one("SELECT * FROM conversations WHERE id=?", (identity,))
        owner = store.one("SELECT owner FROM conversation_owners WHERE conversation_id=?", (identity,))
        if not row or (owner and owner["owner"] != request.state.owner):
            raise HTTPException(404, "Conversation not found")
        row["messages"] = json.loads(row["messages"])
        return row

    @web.get("/api/reports")
    def reports():
        return dict(
            items=store.query(
                "SELECT id,type,created_at,run_id FROM reports ORDER BY created_at DESC LIMIT 100"
            )
        )

    @web.get("/api/reports/{identity}")
    def report(identity: str):
        from app.skills.report import evidence_warning

        row = store.one("SELECT data FROM reports WHERE id=?", (identity,))
        if not row:
            raise HTTPException(404, "Report not found")
        data = json.loads(row["data"])
        warning = evidence_warning(store, data)
        return dict(
            report=data,
            current_evidence_warning=warning,
            publication_status="WITHHELD" if warning else "CURRENT_EVIDENCE_CHECKED",
        )

    # Compatibility aliases reuse the original handlers and permission boundary.
    aliases = {
        "/api/ask": "/api/agent/ask",
        "/api/monitor": "/api/monitor/run",
        "/reports/{ident}/pdf": "/api/reports/{ident}/pdf",
    }
    for route in list(web.routes):
        if getattr(route, "path", None) in aliases:
            web.add_api_route(
                aliases[route.path],
                route.endpoint,
                methods=list(route.methods),
                response_class=route.response_class,
            )
