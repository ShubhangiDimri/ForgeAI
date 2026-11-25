"""Mocked HTTP tests for the optional Groq transport."""
import io
import json
from urllib.error import HTTPError

import pytest

from forgeai import llm
from forgeai.schema import Questions


def test_groq_reads_ignored_dotenv_and_routes_model(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('GROQ_API_KEY="test-only-key"\n')
    model = llm.make_model(llm.GROQ_DEFAULT)
    assert isinstance(llm.make_model("gemma2:2b"), llm.Ollama)

    def response(request, timeout):
        body = json.loads(request.data)
        assert request.full_url == llm.Groq.url
        assert request.get_header("Authorization") == "Bearer test-only-key"
        assert request.get_header("User-agent") == "ForgeAI/1.0"
        assert body["model"] == "openai/gpt-oss-120b"
        assert body["response_format"] == {"type": "json_object"}
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"questions":[]}'}}]}).encode())

    monkeypatch.setattr(llm, "urlopen", response)
    assert model.ask("questions", {}, Questions).questions == []


def test_groq_waits_on_429_and_redacts_http_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    model = llm.make_model(llm.GROQ_JUDGE)
    statuses = iter([429, 401])
    waits = []

    def fail(request, timeout):
        raise HTTPError(request.full_url, next(statuses), "test-only-key",
                        {"Retry-After": "3"}, io.BytesIO(b"test-only-key"))

    monkeypatch.setattr(llm, "urlopen", fail)
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        model.ask("questions", {}, Questions)
    assert waits == [4]
    assert "test-only-key" not in str(error.value)


def test_nvidia_uses_its_own_credentials_and_request_format(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-only")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-only")
    model = llm.make_model("nvidia:nvidia/nemotron-3.5-lightning-30b-a3b")
    def response(request, timeout):
        body = json.loads(request.data)
        assert request.full_url == llm.Nvidia.url
        assert request.get_header("Authorization") == "Bearer nvidia-test-only"
        assert body["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert body["max_tokens"] > 0 and "reasoning_effort" not in body
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"questions":[]}'}}]}).encode())
    monkeypatch.setattr(llm, "urlopen", response)
    assert model.ask("questions", {}, Questions).questions == []
