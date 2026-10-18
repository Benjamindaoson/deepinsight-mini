from app.browser import launch_chromium
from app.config import ROOT
from app.database import Store
from playwright.sync_api import sync_playwright

s = Store()
folder = ROOT / "output/screenshots"
folder.mkdir(parents=True, exist_ok=True)
planning = s.one("SELECT id FROM documents WHERE source_id='city_silk_street' AND status='SOURCE_VERIFIED'")
with sync_playwright() as p:
    browser = launch_chromium(p)
    page = browser.new_page(viewport={"width":1440,"height":1000})
    for path, name in [("/", "ask-ai-gpt.png"), ("/overview", "overview-viewport.png"), ("/monitor", "monitor-viewport.png"),
                       ("/sources/" + planning["id"], "planning-viewport.png")]:
        page.goto("http://127.0.0.1:8766" + path, wait_until="networkidle")
        page.screenshot(path=str(folder / name))
    browser.close()
print("Captured current real product viewports")
