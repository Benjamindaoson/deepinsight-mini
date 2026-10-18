import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.database import Store


def client(tmp_path):
    return TestClient(create_app(Store(tmp_path / "db.sqlite")), base_url="http://localhost")


def test_five_pages_and_cookie_csrf_settings(tmp_path):
    c = client(tmp_path)
    for path in ["/", "/ask", "/monitor", "/reports", "/settings"]:
        response = c.get(path)
        assert response.status_code == 200
        assert "London Office" in response.text
    token = re.search(r'name="csrf-token" content="([^"]+)"', c.get("/settings").text).group(1)
    assert c.post("/api/settings", json={"focus": ["City"]}).status_code == 403
    assert c.post("/api/settings", json={"focus": ["City"]}, headers={"X-CSRF-Token": token, "Origin": "http://evil.example"}).status_code == 403
    response = c.post("/api/settings", json={"focus": ["City"], "morning_time": "08:30"}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert "08:30" in c.get("/settings").text


def test_secret_and_bad_schedule_never_accepted(tmp_path):
    c = client(tmp_path)
    token = re.search(r'name="csrf-token" content="([^"]+)"', c.get("/").text).group(1)
    headers = {"X-CSRF-Token": token}
    assert c.post("/api/settings", json={"morning_time": "25:90"}, headers=headers).status_code == 422
    assert c.post("/api/settings", json={"api_key": "secret"}, headers=headers).status_code == 422
    assert c.get("/source-does-not-exist").status_code == 404


def test_untrusted_host_rejected(tmp_path):
    c = client(tmp_path)
    assert c.get("/", headers={"Host": "evil.example"}).status_code == 400
