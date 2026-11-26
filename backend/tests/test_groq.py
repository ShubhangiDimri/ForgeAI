"""Mocked HTTP tests for the optional Groq transport."""
import io
import json
from urllib.error import HTTPError

import pytest

from forgeai import llm
from forgeai.schema import Questions


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "_credential_paths", lambda: (tmp_path / ".env",))
    for name in ("FORGE_GROQ_KEY_SLOT", "GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4",
                 "NVIDIA_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        monkeypatch.delenv(name, raising=False)


def test_groq_slot_three_uses_the_selected_dotenv_key(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GROQ_API_KEY_1=test-only-first\nGROQ_API_KEY_3=test-only-third\n")
    monkeypatch.setenv("FORGE_GROQ_KEY_SLOT", "3")
    assert llm.make_model(llm.GROQ_DEFAULT)._key == "test-only-third"


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


def test_cloudflare_uses_account_url_and_bearer_token(monkeypatch, tmp_path):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'CLOUDFLARE_API_TOKEN="cf-token-test"\nCLOUDFLARE_ACCOUNT_ID="acct123"\n'
    )
    model = llm.make_model("cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    assert isinstance(model, llm.Cloudflare)
    assert "acct123" in model.url
    assert model._model_name == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    def response(request, timeout):
        body = json.loads(request.data)
        assert "acct123" in request.full_url
        assert request.get_header("Authorization") == "Bearer cf-token-test"
        assert body["model"] == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
        assert body["response_format"] == {"type": "json_object"}
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"questions":[]}'}}]}).encode())

    monkeypatch.setattr(llm, "urlopen", response)
    assert model.ask("questions", {}, Questions).questions == []


def test_cloudflare_retries_on_503_and_raises_on_401(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'CLOUDFLARE_API_TOKEN="cf-token-test"\nCLOUDFLARE_ACCOUNT_ID="acct123"\n'
    )
    model = llm.make_model("cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    statuses = iter([503, 401])
    waits = []

    def fail(request, timeout):
        raise HTTPError(request.full_url, next(statuses), "err",
                        {}, io.BytesIO(b"error"))

    monkeypatch.setattr(llm, "urlopen", fail)
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    with pytest.raises(RuntimeError, match="HTTP 401"):
        model.ask("questions", {}, Questions)
    assert len(waits) == 1  # one retry after 503
    assert "cf-token-test" not in str(waits)


def test_fallback_client_tries_next_provider_on_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'GROQ_API_KEY="groq-key"\nCLOUDFLARE_API_TOKEN="cf-token"\nCLOUDFLARE_ACCOUNT_ID="acct"\n'
    )
    groq = llm.Groq(llm.GROQ_DEFAULT)
    cf = llm.Cloudflare("cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    fallback = llm.FallbackClient("test", [groq, cf])
    calls = []

    def respond(request, timeout):
        calls.append(request.full_url)
        if "groq" in request.full_url:
            raise HTTPError(request.full_url, 429, "rate limit", {"Retry-After": "0"}, io.BytesIO(b""))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"questions":[]}'}}]}).encode())

    monkeypatch.setattr(llm, "urlopen", respond)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    result = fallback.ask("questions", {}, Questions)
    assert result.questions == []
    assert any("groq" in url for url in calls)
    assert any("cloudflare" in url for url in calls)
