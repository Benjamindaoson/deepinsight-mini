"""Actual browser acceptance. Model-blocked results remain BLOCKED, never a live-AI pass."""
import json
import time

import pymupdf as fitz
from playwright.sync_api import sync_playwright, expect

from app.browser import launch_chromium
from app.config import ROOT

OUT = ROOT / "output/evidence/browser"
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = ROOT / "output/screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
QUESTIONS = [
    "Summarise the latest verifiable developments in the London office market. Focus on City, West End and Canary Wharf. Please distinguish verified data from information that is not yet available.",
    "How have prime and Grade A office rents changed in the City and West End? Only compare figures with compatible periods, definitions and units.",
    "What new London office leasing or planning events have been discovered since the previous monitoring run?",
    "Which changes represent meaningful business risks or opportunities, and what evidence supports them?",
    "Generate an executive briefing suitable for a non-technical asset management team, with sources, charts where justified, and clear limitations.",
    "Monitor the London office market now, compare the result with the previous successful snapshot, and show me exactly what changed.",
]
results = {"scope": "Actual browser operations against the running local app", "questions": [], "checks": [], "console_errors": []}


def record(name, **fields):
    results["checks"].append({"name": name, "status": "PASS", **fields})


with sync_playwright() as p:
    browser = launch_chromium(p)
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page = context.new_page()
    page.on("pageerror", lambda err: results["console_errors"].append(str(err)))
    captured = {}
    def capture(response):
        if "/api/jobs/" in response.url and response.status == 200:
            try:
                data = response.json()
            except Exception:
                # A completed monitor intentionally reloads the page; an obsolete poll body may be gone.
                return
            if data.get("status") != "RUNNING":
                captured[data["id"]] = data
    page.on("response", capture)
    page.goto("http://127.0.0.1:8766/", wait_until="networkidle")
    expect(page.get_by_label("Your research question")).to_be_visible()
    page.get_by_role("button",name="New conversation",exact=True).click()
    expect(page.get_by_role("heading",name="What would you like to know about London's office market?")).to_be_visible()
    page.screenshot(path=str(SHOTS / "ask-ai-gpt.png"))
    record("chat_first_default_route")
    page.get_by_role("link",name="Overview",exact=True).click()
    expect(page.get_by_role("heading",name="The market, with its sources.")).to_be_visible()
    expect(page.get_by_role("heading",name="Source-reported market figures")).to_be_visible()
    assert page.locator('.source-metric').count()>10
    page.get_by_label('Submarket',exact=True).select_option('City')
    assert page.locator('.source-metric:not(.hidden)').count()>0
    page.get_by_label('Submarket',exact=True).select_option('all')
    record("dashboard_observations_and_filter",visible_series=page.locator('.source-metric').count())
    assert page.locator('.reported-chart').count()==3
    page.locator('#official-history').screenshot(path=str(SHOTS / 'official-api-charts.png'))
    record('official_api_raw_history_charts',charts=3,approval='Source-reported only; formal report gate unchanged')
    page.screenshot(path=str(SHOTS / "overview.png"), full_page=True)
    page.screenshot(path=str(SHOTS / "overview-viewport.png"))
    record("overview_loaded")
    page.get_by_role("link", name="Market Monitor", exact=True).click()
    with page.expect_response(lambda r: "/api/monitor" in r.url and r.request.method == "POST") as response_info:
        page.get_by_role("button", name="Run Monitor Now", exact=True).click()
    monitor_job = response_info.value.json()["id"]
    page.wait_for_url("**/monitor", wait_until="networkidle")
    # Wait for the page reload after the actual job, not just the already-matching URL.
    page.wait_for_function("() => !document.querySelector('[data-monitor]').disabled", timeout=180000)
    expect(page.get_by_role("heading", name="Run history")).to_be_visible()
    page.screenshot(path=str(SHOTS / "monitor.png"), full_page=True)
    record("manual_monitor", job=captured.get(monitor_job, {}))
    page.get_by_role("link", name="Ask AI", exact=True).click()
    page.get_by_role("button", name="New conversation", exact=True).click()
    for index, question in enumerate(QUESTIONS, 1):
        started = time.monotonic()
        count = page.locator(".chat-entry:not(.user)").count()
        page.get_by_label("Your research question").fill(question)
        with page.expect_response(lambda r: "/api/ask" in r.url and r.request.method == "POST") as response_info:
            page.get_by_role("button", name="Research question", exact=True).click()
        job_id = response_info.value.json()["id"]
        expect(page.locator(".chat-entry:not(.user)")).to_have_count(count + 1, timeout=180000)
        output = page.locator(".chat-entry:not(.user)").last.inner_text()
        page.screenshot(path=str(SHOTS / f"question-{index}.png"), full_page=True)
        job = captured.get(job_id, {})
        actual = job.get("result", {})
        results["questions"].append({"input": question, "actual_output": output,
            "elapsed_seconds": round(time.monotonic() - started, 3), "status": actual.get("status", "UNKNOWN"),
            "model_status": "BLOCKED_HTTP402" if actual.get("status") == "BLOCKED" else actual.get("status"),
            "skill_calls": actual.get("tool_calls", 0), "claims": actual.get("claims", []),
            "stored_source_matches": actual.get("stored_evidence", {}).get("evidence", []),
            "agent_run_id": actual.get("agent_run_id"), "conversation_id": actual.get("conversation_id"),
            "screenshot": str(SHOTS / f"question-{index}.png")})
    page.get_by_label("Your research question").fill("Which of those sources actually covers Canary Wharf, and what is still missing?")
    page.get_by_role("button", name="Research question", exact=True).click()
    expect(page.locator(".chat-entry:not(.user)")).to_have_count(7, timeout=180000)
    record("follow_up_saved", live_ai="BLOCKED")
    page.reload(wait_until="networkidle")
    expect(page.locator(".chat-entry:not(.user)")).to_have_count(7)
    record("conversation_reopen_persistence")
    source = page.locator('.chat-entry a[href^="/sources/"]').first
    source.click()
    expect(page.get_by_role("heading", name="Source extract")).to_be_visible()
    expect(page.get_by_text("Content SHA-256", exact=True)).to_be_visible()
    page.screenshot(path=str(SHOTS / "source-evidence.png"), full_page=True)
    record("source_evidence_access", url=page.url)
    page.get_by_role("link", name="Reports", exact=True).click()
    with page.expect_download(timeout=90000) as download_info:
        page.get_by_role("link", name="Download PDF", exact=True).first.click()
    download = download_info.value
    pdf_path = OUT / "browser-downloaded-briefing.pdf"
    download.save_as(pdf_path)
    pdf = fitz.open(pdf_path)
    pages = []
    for i, pdf_page in enumerate(pdf):
        image = OUT / f"pdf-page-{i+1}.png"
        pdf_page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(image)
        pages.append({"page": i+1, "chars": len(pdf_page.get_text()), "screenshot": str(image)})
    assert all(x["chars"] > 40 for x in pages)
    record("pdf_download_and_render", pages=pages)
    page.get_by_role("link", name="Open report", exact=True).first.click()
    expect(page.get_by_role("heading", name="Executive summary", exact=True)).to_be_visible()
    expect(page.get_by_text("Insufficient comparable observations. Trend charts are withheld.", exact=True)).to_be_visible()
    page.screenshot(path=str(SHOTS / "briefing.png"), full_page=True)
    record("historical_report_open")
    page.goto("http://127.0.0.1:8766/settings")
    page.get_by_label("Morning briefing").fill("08:15")
    page.get_by_role("button", name="Save preferences", exact=True).click()
    expect(page.locator("#settings-result")).to_contain_text("Preferences saved")
    page.reload(wait_until="networkidle")
    expect(page.get_by_label("Morning briefing")).to_have_value("08:15")
    page.get_by_label("Morning briefing").fill("08:00")
    page.get_by_label("Delivery mode").select_option("spool")
    page.get_by_role("button", name="Save preferences", exact=True).click()
    expect(page.locator("#settings-result")).to_contain_text("Preferences saved")
    page.get_by_role("button", name="Send test notification", exact=True).click()
    expect(page.locator("#notification-result")).to_contain_text("CAPTURED_TEST_ONLY")
    page.screenshot(path=str(SHOTS / "settings.png"), full_page=True)
    record("settings_persist_and_isolated_spool_test", external_delivery="NOT SENT")
    page.get_by_label("Delivery mode").select_option("disabled")
    page.get_by_role("button", name="Save preferences", exact=True).click()
    expect(page.locator("#settings-result")).to_contain_text("Preferences saved")
    for route in ["/", "/overview", "/ask", "/monitor", "/reports", "/settings"]:
        page.goto("http://127.0.0.1:8766" + route, wait_until="networkidle")
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), route
    page.screenshot(path=str(SHOTS / "mobile-settings.png"), full_page=True)
    record("five_pages_mobile_no_horizontal_overflow")
    browser.close()
results["real_ai_acceptance"] = "BLOCKED" if any(q["status"] == "BLOCKED" for q in results["questions"]) else "REVIEW_REQUIRED"
results["engineering_browser_status"] = "PASS" if not results["console_errors"] else "PARTIAL"
(OUT / "acceptance.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"questions":len(results["questions"]),"checks":len(results["checks"]),"real_ai":results["real_ai_acceptance"],"browser":results["engineering_browser_status"]}))
