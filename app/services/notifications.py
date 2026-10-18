import hashlib
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import apprise
import httpx

from app.config import config
from app.database import now, uid


def transport_fingerprint(channel, recipient):
    names = {"email": ["MINI_SMTP_HOST", "MINI_SMTP_PORT", "MINI_SMTP_FROM", "MINI_SMTP_USER", "MINI_SMTP_PASSWORD"],
             "telegram": ["MINI_TELEGRAM_TOKEN", "MINI_TELEGRAM_CHAT_ID"], "apprise": ["MINI_APPRISE_URL"]}.get(channel, [])
    return hashlib.sha256(json.dumps([channel, recipient, [os.getenv(n, "") for n in names]], sort_keys=True).encode()).hexdigest()


def email_message(report, html, recipient):
    msg = EmailMessage()
    msg["From"] = os.getenv("MINI_SMTP_FROM", "briefing@localhost")
    msg["To"] = recipient
    msg["Subject"] = "London Office Intelligence | " + report["type"].replace("_", " ").title()
    fingerprint = hashlib.sha256((report["id"] + recipient).encode()).hexdigest()[:32]
    msg["Message-ID"] = f"<{fingerprint}@london-office-intelligence.local>"
    msg.set_content("Your evidence-based market briefing is available. Open the HTML version for source links.")
    msg.add_alternative(html, subtype="html")
    return msg


def send_email(message, *, isolated=False):
    host = os.getenv("MINI_SMTP_HOST", "")
    port = int(os.getenv("MINI_SMTP_PORT", "587"))
    if isolated:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Isolated SMTP tests require a loopback capture server.")
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.send_message(message)
    else:
        if not host:
            raise ValueError("Email transport is not configured.")
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if os.getenv("MINI_SMTP_USER"):
                smtp.login(os.environ["MINI_SMTP_USER"], os.environ["MINI_SMTP_PASSWORD"])
            smtp.send_message(message)
    return "SMTP server accepted message; receipt/read status is unknown"


def dispatch(store, report_id, *, test=False, isolated_smtp=False):
    report = store.one("SELECT * FROM reports WHERE id=?", (report_id,))
    if not report:
        raise ValueError("Report not found.")
    mode = store.setting("notification_mode", "disabled")
    if mode == "disabled" and not isolated_smtp:
        return [{"channel": "external", "status": "DISABLED"}]
    channels = []
    if mode == "spool" or isolated_smtp:
        channels.append(("smtp_test" if isolated_smtp else "spool", "capture@localhost"))
    elif mode == "enabled":
        if store.setting("email_recipient", ""):
            channels.append(("email", store.setting("email_recipient")))
        if store.setting("telegram_enabled", False):
            channels.append(("telegram", "configured_chat"))
        if store.setting("apprise_enabled", False):
            channels.append(("apprise", "configured_target"))
    if not channels:
        return [{"channel": "external", "status": "BLOCKED_CONFIGURATION"}]
    html = Path(report["email_path"]).read_text(encoding="utf-8")
    results = []
    for channel, recipient in channels:
        fingerprint = transport_fingerprint(channel, recipient)
        if channel in {"email", "telegram", "apprise"} and not test:
            receipt = store.setting("channel_test_" + channel, {})
            if receipt.get("fingerprint") != fingerprint or receipt.get("status") != "ACCEPTED":
                results.append({"channel": channel, "status": "BLOCKED_TEST_REQUIRED"})
                continue
        # Test sends use their own identity and can never mark a production report as delivered.
        identity = report_id + ("/test/" + fingerprint[:12] if test else "")
        ident = uid()
        claimed = store.execute("INSERT OR IGNORE INTO notifications VALUES (?,?,?,?,?,?,?,?,?)",
            (ident, identity, channel, recipient, "SENDING", 1, "", "", now()))
        if not claimed:
            old = store.one("SELECT * FROM notifications WHERE report_id=? AND channel=? AND recipient=?", (identity, channel, recipient))
            if old["status"] not in {"FAILED_RETRYABLE"} or old["attempt"] >= 3:
                results.append({"channel": channel, "status": "DEDUPLICATED", "previous_status": old["status"]})
                continue
            ident = old["id"]
            with store.connection() as conn:
                updated = conn.execute("UPDATE notifications SET status='SENDING',attempt=attempt+1 WHERE id=? AND status='FAILED_RETRYABLE'", (ident,)).rowcount
            if not updated:
                results.append({"channel": channel, "status": "DEDUPLICATED"})
                continue
        try:
            message = email_message(report, html, recipient)
            if channel == "spool":
                folder = config().output / "notification_capture"
                folder.mkdir(parents=True, exist_ok=True)
                (folder / (ident + ".eml")).write_bytes(message.as_bytes())
                response, status = "Local EML capture, no external send", "CAPTURED_TEST_ONLY"
            elif channel in {"smtp_test", "email"}:
                response = send_email(message, isolated=channel == "smtp_test")
                status = "ACCEPTED_TEST_ONLY" if channel == "smtp_test" else "ACCEPTED"
            elif channel == "telegram":
                token, chat = os.getenv("MINI_TELEGRAM_TOKEN"), os.getenv("MINI_TELEGRAM_CHAT_ID")
                if not token or not chat:
                    raise ValueError("Telegram credentials are missing.")
                data = json.loads(report["data"])
                url = os.getenv("MINI_PUBLIC_URL", "http://127.0.0.1:8766") + "/reports/" + report_id
                r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=15,
                    json={"chat_id": chat, "text": "London Office Intelligence\n" + "\n".join(data["executive_summary"][:2]) + "\n" + url})
                if r.status_code != 200 or not r.json().get("ok"):
                    raise ValueError("Telegram provider rejected message.")
                response, status = "Telegram provider accepted message", "ACCEPTED"
            else:
                target = os.getenv("MINI_APPRISE_URL", "")
                if not target:
                    raise ValueError("Apprise destination is not configured.")
                client = apprise.Apprise()
                client.add(target)
                if not client.notify(title="London Office Intelligence", body="A new briefing is available."):
                    raise ValueError("Notification provider did not confirm acceptance.")
                response, status = "Apprise accepted message", "ACCEPTED"
            store.execute("UPDATE notifications SET status=?,response=?,message_id=?,updated_at=? WHERE id=?",
                          (status, response, str(message["Message-ID"]), now(), ident))
            if test and status == "ACCEPTED":
                store.set_setting("channel_test_" + channel, {"fingerprint": fingerprint, "status": status, "at": now()})
            results.append({"channel": channel, "status": status})
        except (ConnectionError, ConnectionRefusedError) as exc:
            store.execute("UPDATE notifications SET status='FAILED_RETRYABLE',response=?,updated_at=? WHERE id=?", (type(exc).__name__, now(), ident))
            results.append({"channel": channel, "status": "FAILED_RETRYABLE"})
        except Exception as exc:
            # Ambiguous network failures are not blindly retried: accepted-but-unacknowledged sends may duplicate.
            store.execute("UPDATE notifications SET status='FAILED_REVIEW_REQUIRED',response=?,updated_at=? WHERE id=?", (type(exc).__name__, now(), ident))
            results.append({"channel": channel, "status": "FAILED_REVIEW_REQUIRED"})
    return results
