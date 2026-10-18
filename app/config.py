import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".browsers"))
os.environ.setdefault("PLAYWRIGHT_SKIP_BROWSER_GC", "1")


@dataclass(frozen=True)
class Config:
    data: Path
    output: Path
    key: str
    base_url: str
    model: str
    admin_token: str
    daily_requests: int = 60
    daily_tokens: int = 180000
    max_rounds: int = 5
    max_seconds: int = 150


def config():
    return Config(
        data=Path(os.getenv("MINI_DATA_DIR", ROOT / "data")),
        output=Path(os.getenv("MINI_OUTPUT_DIR", ROOT / "output")),
        key=os.getenv("MINI_API_KEY", os.getenv("LLM_API_KEY", "")),
        base_url=os.getenv("MINI_BASE_URL", os.getenv("LLM_BASE_URL", "https://api.deepseek.com")),
        model=os.getenv("MINI_MODEL", os.getenv("LLM_MODEL", "deepseek-v4-flash")),
        admin_token=os.getenv("MINI_ADMIN_TOKEN", ""),
        daily_requests=int(os.getenv("MINI_DAILY_REQUESTS", "60")),
        daily_tokens=int(os.getenv("MINI_DAILY_TOKENS", "180000")),
    )
