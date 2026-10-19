"""One real SQL/domain-tool agent run on isolated evidence; key stays in memory."""

import hashlib
from app.agent import ask
import json
import sqlite3
import argparse
import re
from dataclasses import replace
from app.config import ROOT, config, runtime_scope
from app.providers import ProviderVault, PROVIDERS
from app.database import Store, now

parser = argparse.ArgumentParser()
parser.add_argument("--revision", default="initial")
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9-]{1,60}", args.revision):
    raise SystemExit("Invalid acceptance revision")
folder = ROOT / (
    "output/evidence/v2-real-agent" + ("" if args.revision == "initial" else "-" + args.revision)
)
folder.mkdir(parents=True, exist_ok=True)
path = folder / "market.sqlite3"
if path.exists():
    raise SystemExit("Preserve existing live acceptance; no implicit retry")
with sqlite3.connect((ROOT / "data/market.sqlite3").as_uri() + "?mode=ro", uri=True) as original:
    with sqlite3.connect(path) as target:
        original.backup(target)
store = Store(path)
vault = ProviderVault(ROOT / "data")
profile = next((p for p in vault.public("workspace")["profiles"] if p["provider"] == "deepseek"), None)
if not profile:
    raise SystemExit("No configured official DeepSeek profile; no fallback provider called")
private = vault.resolve("workspace", profile["id"])
selected = replace(
    config(),
    key=private["key"],
    base_url=PROVIDERS["deepseek"]["base_url"],
    model="deepseek-flash",
    provider="deepseek",
    thinking="auto",
    data=folder,
    output=folder,
    max_rounds=5,
    max_seconds=120,
)
before = {r["id"] for r in store.query("SELECT id FROM model_calls")}
question = (
    "Assess London office evidence coverage for City, West End and Canary Wharf in Q2 2026. "
    "Use get_data_coverage and query_market_metrics to inspect vacancy evidence and review state, "
    "then retrieve an existing primary planning announcement and explain one strictly conditional business implication. "
    "Do not approve observations, run a monitor or publish pending numbers. Quote exact retrieved source text. "
    "Missing evidence is not proof of no market change."
)

with runtime_scope(selected):
    result = ask(store, question)
calls = [
    row
    for row in store.query(
        "SELECT id,at,model,status,input_tokens,output_tokens,latency,error FROM model_calls"
    )
    if row["id"] not in before
]
trace = json.loads(store.one("SELECT trace FROM agent_runs WHERE id=?", (result["agent_run_id"],))["trace"])
receipt = dict(
    at=now(),
    provider="Official DeepSeek",
    model=selected.model,
    question=question,
    result=result,
    requests=calls,
    actual_tools=[t["skill"] for t in trace if t.get("skill")],
    source_files={
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in list((ROOT / "app/analytics").glob("*.py"))
        + list((ROOT / "app/tools").glob("*.py"))
        + [ROOT / "app/agent.py"]
    },
    scope="Actual native SDK calls and tool execution on an online SQLite backup; no source review or external notification changes.",
)
(folder / "RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print(
    json.dumps(
        dict(
            status=result["status"],
            run_id=result["agent_run_id"],
            actual_tools=receipt["actual_tools"],
            requests=len(calls),
            input_tokens=sum(c.get("input_tokens") or 0 for c in calls),
            output_tokens=sum(c.get("output_tokens") or 0 for c in calls),
            accepted_claims=len(result["claims"]),
        )
    )
)
