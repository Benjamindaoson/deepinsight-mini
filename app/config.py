import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_runtime = ContextVar('mini_model_runtime', default=None)
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
    thinking: str = 'auto'
    provider: str = 'deepseek'


@contextmanager
def runtime_scope(selected):
    token = _runtime.set(selected)
    try:
        yield
    finally:
        _runtime.reset(token)


def config():
    if _runtime.get() is not None:
        return _runtime.get()
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
