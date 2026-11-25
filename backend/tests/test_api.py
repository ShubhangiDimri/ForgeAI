"""API endpoint tests using FastAPI TestClient."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_and_providers():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    prov = client.get("/api/providers")
    assert prov.status_code == 200
    ids = {p["id"] for p in prov.json()["providers"]}
    assert {"groq", "nvidia", "cloudflare", "ollama"} <= ids


def test_list_runs_includes_demonstrations():
    res = client.get("/api/runs")
    assert res.status_code == 200
    run_ids = {r["id"] for r in res.json()["runs"]}
    assert "groq-academic-final" in run_ids
    assert "groq-procurement-final" in run_ids


def test_get_run_and_artifact_download():
    res = client.get("/api/runs/groq-academic-final")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scorecards"]) == 2
    assert data["scorecards"][0]["passed"] == 12
    assert data["scorecards"][1]["passed"] == 11
    assert data["final_report"] is not None

    dl = client.get("/api/runs/groq-academic-final/artifacts/scorecards.json")
    assert dl.status_code == 200


def test_path_traversal_blocked():
    res = client.get("/api/runs/groq-academic-final/artifacts/..%2F..%2F.env")
    assert res.status_code in {400, 404}


def test_upload_validation():
    bad = client.post("/api/uploads", files={"files": ("bad.exe", b"mz", "application/octet-stream")})
    assert bad.status_code == 400

    empty = client.post("/api/uploads", files={"files": ("empty.txt", b"", "text/plain")})
    assert empty.status_code == 400

