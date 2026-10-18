import hashlib
import hmac
import json
import os
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import ROOT, config
from app.database import Store, now, uid
from app.services.scheduler import next_slots


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: list[str] = Field(default_factory=lambda: ["City", "West End", "Canary Wharf"], min_length=1, max_length=6)
    morning_time: str = "08:00"
    evening_time: str = "18:00"
    email_recipient: str = Field(default="", max_length=254)
    notification_mode: str = "disabled"
    telegram_enabled: bool = False
    apprise_enabled: bool = False
    vacancy_threshold_pp: float = Field(default=0.2, ge=0.01, le=20)

    @field_validator("morning_time", "evening_time")
    @classmethod
    def time_format(cls, value):
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Use a valid 24-hour time, for example 08:00.")
        return value

    @field_validator("focus")
    @classmethod
    def allowed_focus(cls, value):
        if any(x not in {"City", "West End", "Canary Wharf", "Central London", "Midtown / Fringe"} for x in value):
            raise ValueError("Choose a supported London submarket.")
        return list(dict.fromkeys(value))

    @field_validator("notification_mode")
    @classmethod
    def allowed_mode(cls, value):
        if value not in {"disabled", "spool", "enabled"}:
            raise ValueError("Choose disabled, local capture or enabled.")
        return value

    @field_validator("email_recipient")
    @classmethod
    def email_format(cls, value):
        if value and not re.fullmatch(r"[^\s<>@,;\r\n]+@[^\s<>@,;\r\n]+\.[^\s<>@,;\r\n]+", value):
            raise ValueError("Enter a single valid email address.")
        return value


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


def create_app(store=None):
    store = store or Store()
    web = FastAPI(title="London Office Intelligence", docs_url=None, redoc_url=None)
    web.state.store = store
    web.state.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mini")
    web.state.jobs = {}
    secret_path = store.path.parent / ".session-secret"
    if not secret_path.exists():
        try:
            with secret_path.open("x", encoding="ascii") as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    secret = secret_path.read_text(encoding="ascii").strip().encode()
    renderer = Jinja2Templates(directory=ROOT / "app/templates")
    hosts = ["localhost", "127.0.0.1", "[::1]"]
    if os.getenv("MINI_PUBLIC_HOST"):
        hosts.append(os.environ["MINI_PUBLIC_HOST"])
    web.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    web.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")

    def signed_session():
        token = str(int(time.time())) + ":" + uid()
        return token + "." + hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()

    def valid_session(value):
        if not value or "." not in value:
            return False
        token, signature = value.rsplit(".", 1)
        try:
            if not 0 <= time.time() - int(token.split(":")[0]) <= 43200:
                return False
        except ValueError:
            return False
        return hmac.compare_digest(signature, hmac.new(secret, token.encode(), hashlib.sha256).hexdigest())

    def csrf_for(session):
        return hmac.new(secret, ("csrf:" + session).encode(), hashlib.sha256).hexdigest()

    @web.middleware("http")
    async def boundary(request, call_next):
        path = request.url.path
        if path.startswith("/static/") or path in {"/health", "/login"}:
            response = await call_next(request)
        else:
            session = request.cookies.get("mini_session", "")
            fresh = False
            if not valid_session(session):
                local = request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}
                if local and not config().admin_token:
                    session, fresh = signed_session(), True
                else:
                    return JSONResponse({"detail": "Sign in to continue."}, status_code=401) if path.startswith("/api/") else RedirectResponse("/login", status_code=303)
            request.state.csrf = csrf_for(session)
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                expected_origin = str(request.base_url).rstrip("/")
                if (origin and origin != expected_origin) or not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), request.state.csrf):
                    return JSONResponse({"detail": "This action needs a valid signed session and same-origin confirmation. Reload the page."}, status_code=403)
            response = await call_next(request)
            if fresh:
                response.set_cookie("mini_session", session, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=43200)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @web.exception_handler(Exception)
    async def handled(request, exc):
        store.audit("WEB_ERROR", request.url.path, {"type": type(exc).__name__})
        return JSONResponse({"detail": "The operation could not finish. Your saved evidence is retained. Review Monitor for details."}, status_code=500)

    @web.get("/health")
    def health():
        return {"status": "ok", "product": "London Office Intelligence", "scheduler": "independent"}

    @web.get("/login", response_class=HTMLResponse)
    def login():
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Sign in</title><link rel="stylesheet" href="/static/styles.css"><main class="panel login"><h1>London Office Intelligence</h1><form method="post" action="/login"><label for="token">Administrator access token</label><input id="token" name="token" type="password" autocomplete="current-password" required><div class="actions"><button>Sign in</button></div></form></main></html>'

    @web.post("/login")
    async def do_login(request: Request):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Same-origin sign-in required.")
        data = await request.form()
        expected = config().admin_token
        if not expected or not hmac.compare_digest(str(data.get("token", "")), expected):
            raise HTTPException(403, "Sign-in failed.")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("mini_session", signed_session(), httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=43200)
        return response

    def context(request, page):
        latest = store.one("SELECT * FROM reports ORDER BY created_at DESC LIMIT 1")
        last = store.one("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1")
        successful = store.one("SELECT * FROM monitor_runs WHERE status='SUCCESS' ORDER BY finished_at DESC LIMIT 1")
        return dict(request=request, page=page, csrf=request.state.csrf, latest=latest,
            report=json.loads(latest["data"]) if latest else None, last=last, successful=successful,
            sources=store.query("SELECT * FROM sources"),
            pending=store.one("SELECT count(*) n FROM observations WHERE review_status='PENDING_REVIEW'")["n"],
            blocked=store.setting("model_block"), scheduler=store.setting("scheduler_heartbeat"),
            next_slots=next_slots(store), focus=store.setting("focus", ["City", "West End", "Canary Wharf"]))

    @web.get("/overview", response_class=HTMLResponse)
    def overview(request: Request):
        from app.dashboard import dashboard
        ctx=context(request,"overview")
        ctx['dashboard']=dashboard(store)
        return renderer.TemplateResponse(request=request, name="overview.html", context=ctx)

    @web.get("/", response_class=HTMLResponse)
    @web.get("/ask", response_class=HTMLResponse)
    def ask_page(request: Request):
        from app.dashboard import TOPICS
        ctx = context(request, "ask")
        ctx["conversations"] = store.query("SELECT id,created_at,updated_at,json_extract(messages,'$[0].content') title FROM conversations ORDER BY updated_at DESC LIMIT 20")
        ctx["topics"]=TOPICS
        return renderer.TemplateResponse(request=request, name="ask.html", context=ctx)

    @web.get("/api/dashboard")
    def dashboard_data():
        from app.dashboard import dashboard
        return dashboard(store)

    @web.get("/monitor", response_class=HTMLResponse)
    def monitor_page(request: Request):
        ctx = context(request, "monitor")
        ctx.update(runs=store.query("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 12"),
                   signals=store.query("SELECT * FROM signals ORDER BY created_at DESC LIMIT 15"),
                   slots=store.query("SELECT * FROM schedule_slots ORDER BY claimed_at DESC LIMIT 5"))
        return renderer.TemplateResponse(request=request, name="monitor.html", context=ctx)

    @web.get("/reports", response_class=HTMLResponse)
    def reports_page(request: Request):
        ctx = context(request, "reports")
        ctx["reports"] = store.query("SELECT id,type,created_at,pdf_path FROM reports ORDER BY created_at DESC LIMIT 50")
        return renderer.TemplateResponse(request=request, name="reports.html", context=ctx)

    @web.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        ctx = context(request, "settings")
        ctx["settings"] = {k: store.setting(k, v) for k, v in UserSettings().model_dump().items()}
        c = config()
        ctx.update(provider="Official DeepSeek", model_id=c.model, credential=bool(c.key),
                   notification_test_passed=store.setting("notification_test_passed", False))
        return renderer.TemplateResponse(request=request, name="settings.html", context=ctx)

    @web.post("/api/settings")
    def save_settings(settings: UserSettings):
        old_destination = (store.setting("email_recipient", ""), store.setting("telegram_enabled", False), store.setting("apprise_enabled", False))
        for key, value in settings.model_dump().items():
            store.set_setting(key, value)
        if old_destination != (settings.email_recipient, settings.telegram_enabled, settings.apprise_enabled):
            store.set_setting("notification_test_passed", False)
            for channel in ("email", "telegram", "apprise"):
                store.set_setting("channel_test_" + channel, {})
        store.audit("SETTINGS_SAVED", "preferences", {"fields": list(settings.model_dump())})
        return {"status": "SAVED", "message": "Preferences saved. London-time schedules are used by the independent scheduler."}

    def submit(kind, function):
        if any(job["kind"] == kind and job["status"] == "RUNNING" for job in web.state.jobs.values()):
            raise HTTPException(409, "This operation is already running.")
        ident = uid()
        job = {"id": ident, "kind": kind, "status": "RUNNING", "phase": "Researching" if kind == "ask" else "Collecting sources", "started_at": now()}
        web.state.jobs[ident] = job
        def work():
            try:
                job["result"] = function(ident)
                result_status = job["result"].get("status", "SUCCESS")
                job["status"] = result_status if result_status in {"BLOCKED", "FAILED", "PARTIAL"} else "SUCCESS"
                job["phase"] = "Completed" if job["status"] == "SUCCESS" else job["status"].title()
            except Exception as exc:
                job.update(status="FAILED", phase="Failed", error=str(exc)[:250] if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__)
            job["finished_at"] = now()
        web.state.executor.submit(work)
        return job

    @web.post("/api/monitor")
    def monitor_now():
        from app.skills.monitor import run_monitor
        return submit("monitor", lambda _: run_monitor(store, "manual"))

    @web.post("/api/ask")
    def ask_question(question: Question):
        from app.agent import ask
        return submit("ask", lambda ident: ask(store, question.question, question.conversation_id, run_id=ident))

    @web.get("/api/jobs/{ident}")
    def job_status(ident: str):
        job = web.state.jobs.get(ident)
        if not job:
            raise HTTPException(404, "This live job is no longer available. Saved runs and conversations remain in history.")
        result = dict(job)
        if job["status"] == "RUNNING" and job["kind"] == "monitor":
            run = store.one("SELECT phase FROM monitor_runs WHERE status='RUNNING' ORDER BY started_at DESC LIMIT 1")
            if run:
                result["phase"] = run["phase"]
        elif job["status"] == "RUNNING" and job["kind"] == "ask":
            run = store.one("SELECT trace FROM agent_runs WHERE id=?", (ident,))
            if run:
                trace = json.loads(run["trace"] or "[]")
                skill = trace[-1].get("skill") if trace else None
                result["phase"] = {"research": "Reading sources", "source_reader": "Comparing evidence", "market_data": "Comparing evidence", "compare": "Generating analysis"}.get(skill, "Researching")
        return result

    @web.get("/api/conversations/{ident}")
    def conversation(ident: str):
        row = store.one("SELECT * FROM conversations WHERE id=?", (ident,))
        if not row:
            raise HTTPException(404, "Conversation not found.")
        return {"id": ident, "messages": json.loads(row["messages"]),
                "runs": store.query("SELECT id,question,status,output FROM agent_runs WHERE conversation_id=? ORDER BY started_at", (ident,))}

    @web.post("/api/reports")
    async def save_report(request: Request):
        from app.skills.report import make_report
        body = await request.json()
        result = make_report(store, report_type="on_demand_research", agent_run_id=body.get("agent_run_id"))
        return {"status": "SUCCESS", "report_id": result["id"], "url": "/reports/" + result["id"]}

    @web.get("/reports/{ident}", response_class=HTMLResponse)
    def report_page(ident: str):
        from app.skills.report import rendered_report
        row = store.one("SELECT * FROM reports WHERE id=?", (ident,))
        if not row:
            raise HTTPException(404, "Report not found.")
        return HTMLResponse(rendered_report(store, row))

    @web.get("/reports/{ident}/html")
    def download_html(ident: str):
        from app.skills.report import rendered_report
        row = store.one("SELECT * FROM reports WHERE id=?", (ident,))
        if not row:
            raise HTTPException(404)
        return HTMLResponse(rendered_report(store, row), headers={"Content-Disposition": 'attachment; filename="London-Office-Intelligence-' + ident[:8] + '.html"'})

    @web.get("/reports/{ident}/pdf")
    def download_pdf(ident: str):
        from app.skills.report import export_pdf, evidence_warning
        row = store.one("SELECT * FROM reports WHERE id=?", (ident,))
        if not row:
            raise HTTPException(404)
        warning = evidence_warning(store, json.loads(row["data"]))
        path = Path(row["pdf_path"]) if row["pdf_path"] and not warning else export_pdf(store, ident)
        return FileResponse(path, filename="London-Office-Intelligence-" + ident[:8] + ".pdf", media_type="application/pdf")

    @web.get("/report-assets/{name}")
    def report_asset(name: str):
        if not re.fullmatch(r"[a-f0-9]{32}-chart-\d+\.svg", name):
            raise HTTPException(404)
        path = config().output / "reports" / name
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="image/svg+xml")

    @web.get("/sources/{ident}", response_class=HTMLResponse)
    def source_page(ident: str, request: Request):
        row = store.one("SELECT d.*,s.status source_health FROM documents d JOIN sources s ON s.id=d.source_id WHERE d.id=?", (ident,))
        if not row:
            raise HTTPException(404, "Source not found.")
        ctx = context(request, "sources")
        ctx.update(document=row, observations=store.query("SELECT * FROM observations WHERE document_id=?", (ident,)))
        return renderer.TemplateResponse(request=request, name="source.html", context=ctx)

    @web.post("/api/notifications/test")
    def test_notification():
        from app.services.notifications import dispatch
        row = store.one("SELECT id FROM reports ORDER BY created_at DESC LIMIT 1")
        if not row:
            raise HTTPException(409, "Generate a report first.")
        return {"deliveries": dispatch(store, row["id"], test=True)}

    return web


app = create_app()
