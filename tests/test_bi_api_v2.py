from fastapi.testclient import TestClient
from app.database import Store
from app.main import create_app


def test_bi_api_defaults_to_reviewed_and_keeps_coverage_gaps(tmp_path):
    app = create_app(Store(tmp_path / "db.sqlite3"))
    with TestClient(app, base_url="http://localhost") as client:
        for route in ["overview", "kpis", "trends", "submarkets", "coverage", "events"]:
            response = client.get("/api/dashboard/" + route)
            assert response.status_code == 200
            assert "sources" not in response.text.lower() or "api_key" not in response.text.lower()
        result = client.get("/api/dashboard/overview?geography=Canary%20Wharf&metric=vacancy_rate").json()
        assert result["filters"]["review_status"] == "APPROVED"
        assert not result["observations"] and result["coverage"]
        assert all(r["status"] == "MISSING" for r in result["coverage"])
        assert client.get("/api/dashboard/trends?metric=DROP").status_code == 422


def test_overview_loads_local_echarts_and_real_filter_controls(tmp_path):
    app = create_app(Store(tmp_path / "db.sqlite3"))
    with TestClient(app, base_url="http://localhost") as client:
        page = client.get("/overview")
        assert page.status_code == 200
        for text in [
            "bi-filter-form",
            "bi-dashboard.js",
            "echarts.min.js",
            "Not Verified",
            "Evidence coverage",
        ]:
            assert text in page.text
