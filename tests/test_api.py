from fastapi.testclient import TestClient

from app.main import app
from app.api import routes
from app.models.schemas import ResearchRequest
from app.providers.search import DemoSearchProvider
from app.providers.writer import DemoReportWriter
from app.services.repository import ResearchRepository
from app.services.research import ResearchService


def test_api_research_lifecycle(tmp_path, monkeypatch):
    repo = ResearchRepository(str(tmp_path / "api.sqlite3"))
    monkeypatch.setattr(routes, "service", ResearchService(repo, DemoSearchProvider(), DemoReportWriter()))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        created = client.post("/api/research", json={
            "topic": "Enterprise AI research operations",
            "audience": "Product leadership",
            "focus_questions": ["What are the main risks?"],
        })
        assert created.status_code == 201
        payload = created.json()
        assert payload["status"] == "completed"
        run_id = payload["run_id"]
        detail = client.get(f"/api/research/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["source_count"] >= 3
        markdown = client.get(f"/api/research/{run_id}/markdown")
        assert markdown.status_code == 200
        assert "References" in markdown.text
        listing = client.get("/api/research")
        assert listing.status_code == 200
        assert len(listing.json()) == 1

def test_api_rejects_short_topic():
    with TestClient(app) as client:
        response = client.post("/api/research", json={"topic": "tiny"})
        assert response.status_code == 422

def test_static_dashboard_is_served():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Research Studio" in response.text
        js = client.get("/static/app.js")
        assert js.status_code == 200
