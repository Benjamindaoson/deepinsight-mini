"""Online backup into a new isolated V2 acceptance directory; no source approvals."""

import hashlib
import json
import sqlite3
from app.config import ROOT
from app.database import Store, now

folder = ROOT / "output/evidence/v2-real"
runtime = folder / "runtime"
if runtime.exists():
    raise SystemExit("Preserve previous acceptance; do not overwrite its runtime")
runtime.mkdir(parents=True)
original = ROOT / "data/market.sqlite3"
with sqlite3.connect(original.as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(runtime / "market.sqlite3") as target:
        source.backup(target)
store = Store(runtime / "market.sqlite3")
reviews = store.query("SELECT id,review_status,reviewer,review_reason FROM observations ORDER BY id")
baseline = dict(
    at=now(),
    source=str(original),
    isolated=str(store.path),
    review_digest=hashlib.sha256(json.dumps(reviews, sort_keys=True).encode()).hexdigest(),
    review_states=store.query("SELECT review_status,count(*) n FROM observations GROUP BY review_status"),
    actual_collection="Pending independent APScheduler date trigger",
    model_requests_requested=0,
    scope="Real public collection and actual report/loopback SMTP; controlled schedule, not unattended uptime or fabricated market changes.",
)
store.set_setting("notification_mode", "spool")
store.set_setting("telegram_enabled", False)
store.set_setting("apprise_enabled", False)
store.set_setting(
    "model_block",
    dict(reason="Source-only controlled scheduler acceptance; no model requests authorized by this script."),
)
(folder / "BASELINE.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
print(json.dumps(baseline))
