"""API endpoint tests using FastAPI TestClient."""
import time

import pytest
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



def test_chat_accepts_numbered_groq_keys(monkeypatch):
    from api import main
    from forgeai.runner import Execution
    from forgeai.schema import Answer
    from types import SimpleNamespace

    keys = {"GROQ_API_KEY_1": "mock-1", "GROQ_API_KEY_2": "mock-2"}
    def key(name):
        if name == "FORGE_GROQ_KEY_SLOT":
            return main.llm_mod.os.environ.get(name, "")
        if name not in keys:
            raise RuntimeError("Unavailable test key")
        return keys[name]

    monkeypatch.setattr(main.llm_mod, "provider_key", key)
    monkeypatch.delenv("FORGE_GROQ_KEY_SLOT", raising=False)
    model = main.llm_mod.make_model(main.llm_mod.GROQ_DEFAULT)
    assert model._key == "mock-1"
    monkeypatch.setenv("FORGE_GROQ_KEY_SLOT", "2")
    assert main.llm_mod.make_model(main.llm_mod.GROQ_DEFAULT)._key == "mock-2"

    def runner(run_id, override):
        assert run_id == "groq-academic-final"
        assert override == main.llm_mod.GROQ_DEFAULT
        return SimpleNamespace(model=model, trace=lambda question: Execution(
            answer=Answer(answer=question, citations=[], refused=True)
        ))

    monkeypatch.setattr(main, "_get_runner", runner)
    response = client.post("/api/runs/groq-academic-final/chat", json={
        "question": "test question", "model": main.llm_mod.GROQ_DEFAULT,
    })
    assert response.status_code == 200
    assert response.json()["model"] == main.llm_mod.GROQ_DEFAULT


def test_chat_reports_provider_configuration_failure(monkeypatch):
    from api import main

    def unavailable(*_):
        raise RuntimeError("Test credential missing")

    monkeypatch.setattr(main, "_get_runner", unavailable)
    response = client.post("/api/runs/groq-academic-final/chat", json={"question": "test question"})
    assert response.status_code == 503
    assert "Test credential missing" in response.json()["detail"]


@pytest.mark.parametrize("interactive", [False, True])
def test_build_uses_shared_factory(tmp_path, monkeypatch, interactive):
    from api import main
    from forgeai.retrieval import Index
    from tests.test_factory import Encoder, Scripted

    demo = tmp_path / "demo" / "academic"
    demo.mkdir(parents=True)
    (demo / "policy.txt").write_text("Attendance minimum is 75 percent.")
    monkeypatch.setattr(main, "DEMO_DATA_DIR", demo.parent)
    monkeypatch.setattr(main, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(main.llm_mod, "make_model", lambda _: Scripted())
    monkeypatch.setattr(main.gen_mod, "Index", lambda docs, settings, model:
                        Index(docs, settings, model, Encoder()))
    response = client.post("/api/builds", json={
        "brief": "Build an assistant for student policies.",
        "demo_dataset": "academic", "prototype_only": True, "interactive": interactive,
    })
    assert response.status_code == 200
    ids = response.json()
    url = f"/api/builds/{ids['build_id']}"

    def wait_for(status):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = client.get(url).json()
            assert state["status"] != "failed", state["error"]
            if state["status"] == status:
                return state
            time.sleep(0.02)
        pytest.fail(f"Build did not reach {status}")

    if interactive:
        assert wait_for("waiting_intake")["questions"] == ["Preferred format?"]
        assert client.post(url+"/intake", json={"answers": ["Concise"]}).status_code == 200
        review = wait_for("waiting_approval")
        assert review["coverage"]["scholarships"]["status"] == "unsupported"
        assert client.post(url+"/approve", json={"requirements": review["requirements"]}).status_code == 200

    wait_for("completed")
    run = client.get(f"/api/runs/{ids['run_id']}").json()
    assert "scholarships" in run["requirements"]["must_refuse"]
    assert run["document_manifest"]


def test_resume_does_not_modify_completed_demo():
    result = client.post("/api/runs/groq-academic-final/resume", json={"mode": "scoring"})
    assert result.status_code == 409
