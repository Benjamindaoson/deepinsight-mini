"""Verify actual scheduled collection, restart dedupe, PDF and loopback SMTP."""

import pymupdf
from app.skills.report import export_pdf
from app.services.notifications import dispatch

import hashlib
import json
import os
import socketserver
import threading
from dataclasses import replace
from datetime import datetime
from email import policy
from email.parser import BytesParser
from app.config import ROOT, config, runtime_scope
from app.database import Store, now
from app.monitoring.scheduler import execute_slot

folder = ROOT / "output/evidence/v2-real"
store = Store(folder / "runtime/market.sqlite3")
run = store.one("SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1")
assert run["status"] == "SUCCESS" and run["success_count"] == run["source_count"] == 7
slot = store.one("SELECT * FROM schedule_slots ORDER BY claimed_at DESC LIMIT 1")
assert slot["run_id"] == run["id"] and slot["status"] == "SUCCESS"
replay = execute_slot(store, "morning", datetime.fromisoformat(slot["claimed_at"]))
assert replay["deduplicated"]
baseline = json.loads((folder / "BASELINE.json").read_text())
reviews = store.query("SELECT id,review_status,reviewer,review_reason FROM observations ORDER BY id")
assert hashlib.sha256(json.dumps(reviews, sort_keys=True).encode()).hexdigest() == baseline["review_digest"]
captured = []


class Capture(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 localhost isolated Mini V2 SMTP\r\n")
        while line := self.rfile.readline(8192):
            command = line.decode("ascii", "replace").strip().upper()
            if command.startswith("EHLO"):
                self.wfile.write(b"250-localhost\r\n250 SIZE 10485760\r\n")
            elif command.startswith(("HELO", "MAIL", "RCPT", "RSET", "NOOP")):
                self.wfile.write(b"250 OK\r\n")
            elif command == "DATA":
                self.wfile.write(b"354 End with dot\r\n")
                body = bytearray()
                while (part := self.rfile.readline(65536)) not in (b".\r\n", b""):
                    body.extend(part[1:] if part.startswith(b"..") else part)
                    if len(body) > 10_000_000:
                        return
                captured.append(bytes(body))
                self.wfile.write(b"250 Accepted locally\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                return
            else:
                self.wfile.write(b"502 Unsupported command\r\n")


selected = replace(config(), data=folder / "runtime", output=folder)
with runtime_scope(selected):
    pdf = export_pdf(store, run["report_id"])
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Capture) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        os.environ["MINI_SMTP_HOST"] = "127.0.0.1"
        os.environ["MINI_SMTP_PORT"] = str(server.server_address[1])
        first = dispatch(store, run["report_id"], test=True, isolated_smtp=True)
        second = dispatch(store, run["report_id"], test=True, isolated_smtp=True)
        server.shutdown()
assert len(captured) == 1
msg = BytesParser(policy=policy.default).parsebytes(captured[0])
body = msg.get_body(preferencelist=("html",)).get_content()
assert "View full report" in body and "Download PDF" in body
(folder / "actual-smtp.eml").write_bytes(captured[0])
(folder / "actual-email.html").write_text(body, encoding="utf-8")

pdf_doc = pymupdf.open(pdf)
for index, page in enumerate(pdf_doc):
    page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(folder / f"pdf-page-{index + 1}.png")
receipt = dict(
    at=now(),
    status="PASS_CONTROLLED_LIVE_SCHEDULER",
    run=run,
    slot=slot,
    restart_duplicate=replay,
    unchanged_review_states=True,
    source_endpoints=7,
    new_documents=run["new_documents"],
    new_events=run["new_events"],
    verified_signals=run["valid_signals"],
    pdf_path=str(pdf),
    pdf_pages=len(pdf_doc),
    smtp_first=first,
    smtp_second=second,
    messages_received=len(captured),
    model_requests=0,
    external_delivery=False,
    limitation="A real APScheduler date trigger exercised the existing full collection/report pipeline. Cron times are separately tested; multi-day uptime and external email receipt are not claimed.",
)
(folder / "RECEIPT.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in receipt.items() if k not in ["run", "slot"]}))
