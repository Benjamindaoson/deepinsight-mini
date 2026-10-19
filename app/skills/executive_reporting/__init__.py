import json
from app.tools.contracts import ReportInput
from typing import Literal


class ExportInput(ReportInput):
    format: Literal["html", "pdf"] = "html"


def generate_market_briefing(store, args):
    from app.skills.report import make_report

    result = make_report(store, report_type="on_demand_research")
    return dict(
        report_id=result["id"],
        url="/reports/" + result["id"],
        evidence_ids=[s["id"] for s in result["data"].get("sources", [])],
    )


def verify_report(store, args):
    from app.skills.report import evidence_warning

    row = store.one("SELECT * FROM reports WHERE id=?", (args.report_id,))
    if not row:
        raise ValueError("REPORT_NOT_FOUND")
    data = json.loads(row["data"])
    warning = evidence_warning(store, data)
    return dict(
        report_id=row["id"],
        publication_status="WITHHELD" if warning else "CURRENT_EVIDENCE_CHECKED",
        evidence_ids=[s["id"] for s in data.get("sources", [])],
        warnings=[warning] if warning else [],
        semantic_approval=False,
    )


def export_report(store, args):
    result = verify_report(store, args)
    if args.format == "pdf":
        from app.skills.report import export_pdf

        export_pdf(store, args.report_id)
    result["url"] = "/reports/" + args.report_id + ("/pdf" if args.format == "pdf" else "/html")
    return result
