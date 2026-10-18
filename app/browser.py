"""Project-local Playwright browser, with installed Chromium Edge fallback on Windows."""
import os
from pathlib import Path


def launch_chromium(playwright):
    channel = os.getenv("MINI_BROWSER_CHANNEL")
    if channel:
        return playwright.chromium.launch(headless=True, channel=channel)
    executable = Path(playwright.chromium.executable_path)
    if executable.exists():
        return playwright.chromium.launch(headless=True, executable_path=str(executable))
    if os.name == "nt" and Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe").exists():
        return playwright.chromium.launch(headless=True, channel="msedge")
    raise ValueError("Install the project Playwright Chromium browser; see RUNBOOK browser setup.")
