import json
import base64
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import ROOT, config
from app.database import now, uid
from app.skills.compare import period_key
from app.analytics.publication import approved_observations, verified_metric_signals
from app.tools.contracts import document as verified_document


def templates():
    return Environment(
        loader=FileSystemLoader(ROOT / "app/templates"), autoescape=select_autoescape(["html", "xml"])
    )


def charts(store, report_id, folder):
    rows = approved_observations(store)
    groups = defaultdict(list)
    for row in rows:
        period = period_key(row["period"])
        if period:
            groups[
                tuple(row[k] for k in ("metric", "geography", "definition", "unit", "publisher", "source_id"))
                + (period[0],)
            ].append(row)
    result = []
    for key, observations in groups.items():
        # Duplicate period values or revisions cannot become a continuous series.
        by_period = defaultdict(list)
        for obs in observations:
            by_period[obs["period"]].append(obs)
        if any(len({r["value"] for r in group}) > 1 for group in by_period.values()):
            continue
        series = sorted((group[0] for group in by_period.values()), key=lambda row: row["period"])
        if len(series) < 2 or any(
            b["comparison_status"] != "COMPARABLE" or b["previous_observation_id"] != a["id"]
            for a, b in zip(series, series[1:])
        ):
            continue
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 2.8), layout="constrained")
        ax.plot([o["period"] for o in series], [o["value"] for o in series], color="#168c87", marker="o")
        title = key[1] + " " + key[0].replace("_", " ")
        ax.set(title=title, ylabel=key[3])
        ax.grid(axis="y", alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
        file = folder / f"{report_id}-chart-{len(result)}.svg"
        fig.savefig(file, format="svg")
        plt.close(fig)
        result.append(
            {
                "title": title,
                "file": str(file),
                "url": "/report-assets/" + file.name,
                "data_uri": "data:image/svg+xml;base64," + base64.b64encode(file.read_bytes()).decode(),
                "definition": key[2],
                "publisher": key[4],
                "observation_ids": [o["id"] for o in series],
            }
        )
    return result


def make_report(store, run_id=None, *, report_type=None, agent_run_id=None):
    store.invalidate()
    run = (
        store.one("SELECT * FROM monitor_runs WHERE id=?", (run_id,))
        if run_id
        else store.one("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1")
    )
    report_id = uid()
    folder = config().output / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    health = store.query("SELECT id,name,url,status,last_success,last_attempt,error FROM sources")
    docs = store.query("""SELECT d.id,d.title,d.url,d.publisher,d.published_at,d.discovered_at,d.geography,d.status,d.hash,
        s.status source_health FROM documents d JOIN sources s ON s.id=d.source_id
        WHERE d.status='SOURCE_VERIFIED' ORDER BY d.published_at DESC LIMIT 30""")
    approved = sorted(approved_observations(store), key=lambda row: row["period"], reverse=True)
    signals = verified_metric_signals(store, approved)[:12]
    pending = store.one("SELECT count(*) n FROM observations WHERE review_status='PENDING_REVIEW'")["n"]
    baseline = bool(run and run.get("baseline"))
    failed = [s for s in health if s["status"] != "HEALTHY"]
    if not run or run["status"] not in {"SUCCESS", "PARTIAL"}:
        summary = ["Incomplete source collection. Market changes cannot be assessed from this check."]
    elif baseline:
        summary = [
            f"Baseline established from {run['success_count']} accessible source endpoints. Indexed material may predate this check."
        ]
    elif run["new_documents"]:
        summary = [
            f"{run['new_documents']} newly indexed or revised documents since the previous check. Source updates require market interpretation."
        ]
    else:
        summary = [
            "No new document versions detected at the successfully checked endpoints. This does not establish that the wider market was unchanged."
        ]
    summary.append(
        f"{len(signals)} active approved quantitative signals. {pending} candidate observations remain pending review."
    )
    summary.append(
        "City and West End evidence is available only where sources are listed. Dedicated Canary Wharf coverage remains incomplete."
    )
    summary.append(
        f"{len(failed)} source endpoints have incomplete coverage."
        if failed
        else "All enabled source endpoints responded in the latest check."
    )
    highlights = store.query("""SELECT e.*,d.url,s.status source_health FROM events e
        JOIN documents d ON d.id=e.document_id JOIN sources s ON s.id=d.source_id
        WHERE e.status='SOURCE_VERIFIED' AND d.status='SOURCE_VERIFIED'
        ORDER BY e.discovered_at DESC LIMIT 10""")
    for event in highlights:
        event["is_new_discovery"] = bool(
            run and not baseline and event["discovered_at"] >= (run.get("started_at") or "")
        )
    cards = []
    for metric, name in [
        ("prime_rent", "Prime rent"),
        ("grade_a_rent", "Grade A rent"),
        ("vacancy_rate", "Vacancy"),
        ("availability", "Availability"),
        ("take_up", "Take-up"),
        ("supply", "Supply"),
    ]:
        obs = next((o for o in approved if o["metric"] == metric), None)
        cards.append({"name": name, "observation": obs})
    date = datetime.fromisoformat(now()).astimezone(ZoneInfo("Europe/London"))
    trigger = report_type or ((run or {}).get("trigger") or "on_demand")
    trigger = {"once": "on_demand", "manual": "on_demand", "agent_requested": "on_demand"}.get(
        trigger, trigger
    )
    data = dict(
        report_id=report_id,
        generated_at=now(),
        date_label=date.strftime("%d %B %Y"),
        coverage_as_of=run.get("finished_at") or now() if run else now(),
        report_type=trigger,
        coverage_status=(run or {}).get("status", "NO_RUN"),
        baseline=baseline,
        executive_summary=summary,
        market_signals=signals,
        indicator_cards=cards,
        event_highlights=highlights,
        risks=[
            {
                "fact": "Coverage and approval gaps remain.",
                "interpretation": "An absent signal is not evidence that an asset or submarket is unaffected.",
                "next": "Validate current market publications and review definitions before decisions.",
            }
        ],
        opportunities=[
            {
                "fact": "Primary sources and publication dates can be reviewed together.",
                "interpretation": "Use newly discovered evidence to prioritize analyst follow-up.",
                "next": "Check planning status, location and transaction details against the original publication.",
            }
        ],
        watchlist=store.setting("focus", ["City", "West End", "Canary Wharf"]),
        sources=docs,
        source_health=health,
        charts=charts(store, report_id, folder),
        methodology="Deterministic body fingerprints, URL/content/event deduplication, original publication dates and separate discovery timestamps. Numeric comparisons require explicit human approval, same publisher, geography, definition, units and period frequency. Planning approval is not completed supply.",
        limitations=[
            "A small public-source PoC, not comprehensive market coverage.",
            "Source verification does not approve numeric interpretation. No approved comparable history means no trend chart.",
            "AI material is included only after a successful real model run and evidence validation. Model interpretations still require analyst review.",
            "Discovery dates do not establish when a market event occurred. Baseline documents are not new market changes.",
            "No investment recommendation or measured financial return is claimed.",
        ],
        pending_count=pending,
        ai_status="NOT_REQUESTED",
        generation_status="PARTIAL" if approved else "INSUFFICIENT_EVIDENCE",
        query=None,
        agent_analysis=None,
    )
    if agent_run_id:
        agent_run = store.one("SELECT * FROM agent_runs WHERE id=?", (agent_run_id,))
        if agent_run and agent_run["status"] == "SUCCESS":
            from app.agent import validate_answer

            data["agent_analysis"] = validate_answer(store, json.loads(agent_run["output"]))
            data["ai_status"] = "DRAFT_REVIEW_REQUIRED"
            data["query"] = agent_run["question"]
    env = templates()
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    html = env.get_template("briefing.html").render(report=data, css=css, standalone=True)
    email = env.get_template("email.html").render(
        report=data, base_url=__import__("os").getenv("MINI_PUBLIC_URL", "http://127.0.0.1:8766")
    )
    html_path, email_path = folder / f"{report_id}.html", folder / f"{report_id}-email.html"
    html_path.write_text(html, encoding="utf-8")
    email_path.write_text(email, encoding="utf-8")
    store.execute(
        "INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)",
        (
            report_id,
            (run or {}).get("id"),
            str(data["report_type"]),
            now(),
            json.dumps(data),
            str(html_path),
            str(email_path),
            None,
        ),
    )
    return {"id": report_id, "data": data, "html_path": str(html_path), "email_path": str(email_path)}


def evidence_warning(store, data):
    ids = {d["id"] for d in data.get("sources", [])}
    stale = store.query(
        "SELECT d.id FROM documents d JOIN sources s ON s.id=d.source_id WHERE d.status!='SOURCE_VERIFIED' OR s.status!='HEALTHY'"
    )
    obs_ids = {c["observation"]["id"] for c in data.get("indicator_cards", []) if c.get("observation")}
    for chart in data.get("charts", []):
        obs_ids.update(chart.get("observation_ids", []))
    for signal in data.get("market_signals", []):
        obs_ids.update([signal.get("observation_id"), signal.get("previous_observation_id")])
    for claim in (data.get("agent_analysis") or {}).get("claims", []):
        ids.add(claim["document_id"])
        if claim.get("observation_id"):
            obs_ids.add(claim["observation_id"])
    invalid_obs = store.query("""SELECT o.id FROM observations o LEFT JOIN documents d ON d.id=o.document_id
        LEFT JOIN sources s ON s.id=d.source_id WHERE o.review_status!='APPROVED' OR d.status!='SOURCE_VERIFIED' OR s.status!='HEALTHY'""")
    invalid = any(d["id"] in ids for d in stale) or any(o["id"] in obs_ids for o in invalid_obs)
    ids.update(event["document_id"] for event in data.get("event_highlights", []) if event.get("document_id"))
    for identity in obs_ids:
        row = store.one("SELECT document_id FROM observations WHERE id=?", (identity,))
        if not row:
            invalid = True
        elif row["document_id"]:
            ids.add(row["document_id"])
    for identity in ids:
        try:
            verified_document(store, identity)
        except (OSError, ValueError):
            invalid = True
    for saved_source in data.get("sources", []):
        current = store.one("SELECT published_at FROM documents WHERE id=?", (saved_source["id"],))
        invalid |= not current or current["published_at"] != saved_source.get("published_at")
    for signal in data.get("market_signals", []):
        row = store.one("SELECT status FROM signals WHERE id=?", (signal["id"],))
        invalid |= not row or row["status"] != "ACTIVE"
    return (
        "Historical briefing. Supporting evidence has changed, been withdrawn or become unavailable. Saved figures and interpretations are an archival snapshot, not current valid conclusions."
        if invalid
        else None
    )


def rendered_report(store, row):
    data = json.loads(row["data"])
    data["current_warning"] = evidence_warning(store, data)
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    return templates().get_template("briefing.html").render(report=data, css=css, standalone=True)


def export_pdf(store, report_id):
    from playwright.sync_api import sync_playwright

    row = store.one("SELECT * FROM reports WHERE id=?", (report_id,))
    if not row:
        raise ValueError("Report not found.")
    data = json.loads(row["data"])
    warning = evidence_warning(store, data)
    path = Path(row["html_path"]).with_name(row["id"] + ("-historical-warning.pdf" if warning else ".pdf"))
    with sync_playwright() as p:
        from app.browser import launch_chromium

        browser = launch_chromium(p)
        page = browser.new_page()
        page.set_content(rendered_report(store, row), wait_until="networkidle")
        # Local chart files are selected by the server; never from retrieved source HTML.
        chart_data = json.loads(row["data"])["charts"]
        for chart in chart_data:
            if not chart.get("data_uri"):
                uri = (
                    "data:image/svg+xml;base64," + base64.b64encode(Path(chart["file"]).read_bytes()).decode()
                )
                page.locator('img[src="' + chart["url"] + '"]').evaluate("(el, src) => el.src = src", uri)
        page.locator("img").evaluate_all("imgs => Promise.all(imgs.map(img => img.decode()))")
        page.pdf(
            path=str(path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<span style="font-size:8px;margin-left:28px;color:#536273">London Office Intelligence</span>',
            footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#536273">Research briefing | <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
            margin={"top": "16mm", "bottom": "18mm", "left": "12mm", "right": "12mm"},
        )
        browser.close()
    store.execute("UPDATE reports SET pdf_path=? WHERE id=?", (str(path), report_id))
    return path
