"""A real SMTP exchange with a loopback-only isolated capture endpoint."""
import json
import os
import socketserver
import threading
from email import policy
from email.parser import BytesParser

from app.config import ROOT
from app.database import Store, now
from app.services.notifications import dispatch

folder = ROOT / "output/evidence/smtp"
folder.mkdir(parents=True, exist_ok=True)
captured = []


class Capture(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 localhost isolated SMTP acceptance\r\n")
        while line := self.rfile.readline(8192):
            command = line.decode("ascii", "replace").strip().upper()
            if command.startswith("EHLO"):
                self.wfile.write(b"250-localhost\r\n250 SIZE 10485760\r\n")
            elif command.startswith(("HELO", "MAIL", "RCPT", "RSET", "NOOP")):
                self.wfile.write(b"250 OK\r\n")
            elif command == "DATA":
                self.wfile.write(b"354 End with dot\r\n")
                content = bytearray()
                while (part := self.rfile.readline(65536)) not in (b".\r\n", b""):
                    content.extend(part[1:] if part.startswith(b"..") else part)
                    if len(content) > 10 * 1024 * 1024:
                        return
                captured.append(bytes(content))
                self.wfile.write(b"250 Captured locally\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                return
            else:
                self.wfile.write(b"502 Unsupported command\r\n")


store = Store()
report = store.one("SELECT id FROM reports ORDER BY created_at DESC LIMIT 1")
with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Capture) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    os.environ["MINI_SMTP_HOST"] = "127.0.0.1"
    os.environ["MINI_SMTP_PORT"] = str(server.server_address[1])
    delivery = dispatch(store, report["id"], test=True, isolated_smtp=True)
    duplicate = dispatch(store, report["id"], test=True, isolated_smtp=True)
    server.shutdown()
assert len(captured) == 1
msg = BytesParser(policy=policy.default).parsebytes(captured[0])
html = msg.get_body(preferencelist=("html",)).get_content()
assert "View full report" in html and "Download PDF" in html and "London Office Intelligence" in html
(folder / "captured.eml").write_bytes(captured[0])
(folder / "captured-email.html").write_text(html, encoding="utf-8")
receipt = {"status": "PASS_ISOLATED_SMTP", "at": now(), "report_id": report["id"],
    "delivery": delivery, "second_attempt": duplicate, "messages_received": len(captured),
    "message_id": str(msg["Message-ID"]), "external_delivery": "NOT SENT / NOT VERIFIED",
    "scope": "Loopback SMTP recipient accepted the actual HTML MIME email. No claim of external receipt or user reading."}
(folder / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
