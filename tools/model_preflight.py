"""One small real connectivity probe. Never print provider bodies or credentials."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = os.getenv("MINI_BASE_URL", os.getenv("LLM_BASE_URL", "https://api.deepseek.com"))
model = os.getenv("MINI_MODEL", os.getenv("LLM_MODEL", "deepseek-v4-flash"))
key = os.getenv("MINI_API_KEY", os.getenv("LLM_API_KEY", ""))
receipt = {"provider": urllib.parse.urlsplit(base).hostname, "model": model,
           "test": "REAL API connectivity, not Agent acceptance", "status": "BLOCKED"}
start = time.monotonic()
if key:
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "messages": [{"role": "user", "content": "Reply OK only."}],
                         "max_tokens": 16, "stream": False}).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            obj = json.load(response)
        receipt.update(status="PASS" if obj.get("choices") else "FAIL",
            returned_model=obj.get("model"), usage=obj.get("usage"),
            output=obj.get("choices", [{}])[0].get("message", {}).get("content", "")[:80])
    except urllib.error.HTTPError as exc:
        receipt.update(status="BLOCKED", error=f"Provider HTTP {exc.code}")
    except Exception as exc:
        receipt.update(status="BLOCKED", error=type(exc).__name__)
else:
    receipt["error"] = "No environment credential"
receipt["elapsed_seconds"] = round(time.monotonic() - start, 3)
folder = root / "output/evidence"
folder.mkdir(parents=True, exist_ok=True)
(folder / "G0-model-smoke.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
