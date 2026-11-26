import json
import os
import time
import random
from email.utils import parsedate_to_datetime
from threading import Lock
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).with_name("prompts")
OUTPUT_BUDGET = {"questions": 160, "requirements": 320, "coverage": 180, "design": 320,
                 "route": 150, "answer": 240, "answer_precise": 240, "eval_generate": 260, "eval_multi_document": 260, "eval_questions": 220, "eval_outside": 160, "eval_validate": 72, "judge": 160}


class ModelClient:
    model: str
    url: str

    def output_budget(self, stage: str, attempt: int) -> int:
        return min(640, OUTPUT_BUDGET.get(stage, 320) * (attempt + 1))

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        raise NotImplementedError

    def ask(self, stage: str, payload: dict, schema: type[T]) -> T:
        system = (PROMPTS / "boundary.txt").read_text() + "\n" + (PROMPTS / f"{stage}.txt").read_text()
        system += "\nResponse schema: " + json.dumps(schema.model_json_schema())
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        for attempt in range(2):
            budget = self.output_budget(stage, attempt)
            try:
                return schema.model_validate_json(self.complete(messages, schema, budget))
            except (URLError, TimeoutError) as exc:
                raise RuntimeError(f"{type(self).__name__} {self.model}: provider offline or connection failed") from exc
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                if attempt:
                    raise ValueError(f"Invalid {stage} output after two attempts: {str(exc)[:400]}") from exc
                messages.append({"role": "user", "content": f"Correct the JSON for this validation error: {str(exc)[:400]}"})
        raise AssertionError("unreachable")


class Ollama(ModelClient):
    def __init__(self, model: str):
        self.model = model
        self.url = os.getenv("FORGE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        body = dict(model=self.model, messages=messages, format=schema.model_json_schema(),
                    stream=False, options={"temperature": 0, "num_ctx": 4096,
                                           "num_predict": budget, "num_thread": 4})
        req = Request(self.url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=240) as response:
            return json.load(response)["message"]["content"]


GROQ_DEFAULT = "groq:openai/gpt-oss-120b"
GROQ_JUDGE = "groq:openai/gpt-oss-20b"


def _credential_paths() -> tuple[Path, ...]:
    return tuple(dict.fromkeys((Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env")))


def provider_key(variable: str) -> str:
    """Read one provider credential from the environment or the project-root .env."""
    if value := os.getenv(variable, "").strip():
        return value
    for path in _credential_paths():
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, _, value = line.strip().removeprefix("export ").partition("=")
                if name.strip() == variable:
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                        value = value[1:-1]
                    if value:
                        return value
    raise RuntimeError(f"Set {variable} in the environment or in the project-root .env")


def groq_credentials() -> list[tuple[str, str]]:
    try:
        slot = provider_key("FORGE_GROQ_KEY_SLOT")
    except RuntimeError:
        slot = ""
    if slot not in {"", "1", "2", "3", "4"}:
        raise RuntimeError("FORGE_GROQ_KEY_SLOT must be 1, 2, 3 or 4")
    names = ["GROQ_API_KEY", *(f"GROQ_API_KEY_{i}" for i in range(1, 5))]
    if slot:
        preferred = f"GROQ_API_KEY_{slot}"
        names.remove(preferred)
        names.insert(0, preferred)
    credentials = []
    seen = set()
    for name in names:
        try:
            key = provider_key(name)
            if key not in seen:
                credentials.append((name, key))
                seen.add(key)
        except RuntimeError:
            continue
    if not credentials:
        raise RuntimeError(f"Set {' or '.join(names)} in backend/.env or the environment")
    return credentials


def groq_key() -> str:
    return groq_credentials()[0][1]


class ProviderError(RuntimeError):
    def __init__(self, model: str, status: int, delay: float = 0):
        self.status = status
        self.retry_after = delay
        suffix = f". Retry after {delay:.0f} seconds." if delay else ""
        super().__init__(f"{model} returned HTTP {status}{suffix}")


_COOLDOWNS: dict[tuple[str, int], float] = {}
_COOLDOWN_LOCK = Lock()


def provider_response(request: Request, model: str, credential: str, timeout: int, *, wait_for_rate_limit: bool = True) -> dict:
    key = (model, hash(credential))
    for attempt in range(3):
        with _COOLDOWN_LOCK:
            remaining = _COOLDOWNS.get(key, 0) - time.monotonic()
        if remaining > 0:
            raise ProviderError(model, 429, remaining)
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            status = exc.code
            header = exc.headers.get("Retry-After", "")
            exc.close()
            if status == 400:
                raise ValueError(f"{model} rejected the request or could not produce JSON") from None
            try:
                requested = float(header)
            except ValueError:
                try:
                    requested = parsedate_to_datetime(header).timestamp() - time.time()
                except (ValueError, TypeError, OverflowError):
                    requested = 0
            minimum = (4 if status == 429 else 1) * 2 ** attempt
            delay = max(minimum, requested) + (random.uniform(0, 0.5) if attempt else 0)
            deadline = time.monotonic() + delay
            if status == 429:
                with _COOLDOWN_LOCK:
                    _COOLDOWNS[key] = max(_COOLDOWNS.get(key, 0), deadline)
            if ((status == 429 and not wait_for_rate_limit) or attempt == 2
                    or status not in {429, 500, 502, 503, 504} or delay > 12):
                raise ProviderError(model, status, delay if status in {429, 503} else 0) from None
            time.sleep(delay)
            if status == 429:
                with _COOLDOWN_LOCK:
                    if _COOLDOWNS.get(key) == deadline:
                        _COOLDOWNS.pop(key, None)
    raise AssertionError("unreachable")


class HostedClient(ModelClient):
    """Share the JSON response and retry handling across hosted providers."""

    key_variable: str

    def __init__(self, model: str):
        self.model = model
        self._key = provider_key(self.key_variable)

    def output_budget(self, stage: str, attempt: int) -> int:
        return 1100 * (attempt + 1)

    def payload(self, messages: list[dict], budget: int) -> dict:
        return {"model": self.model.split(":", 1)[1], "messages": messages,
                "temperature": 0, "response_format": {"type": "json_object"}}

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        return self._complete_with_key(messages, budget, self._key)

    def _complete_with_key(self, messages: list[dict], budget: int, key: str, *, wait_for_rate_limit: bool = True) -> str:
        body = self.payload(messages, budget)
        provider = type(self).__name__
        print(f"[ForgeAI] {provider} {body['model']} budget={budget}", flush=True)
        request = Request(self.url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "User-Agent": "ForgeAI/1.0",
            "Authorization": f"Bearer {key}"})
        data = provider_response(request, self.model, key, 45, wait_for_rate_limit=wait_for_rate_limit)
        return data["choices"][0]["message"]["content"]


class Groq(HostedClient):
    key_variable = "GROQ_API_KEY"
    url = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model: str):
        self.model = model
        self._credentials = groq_credentials()
        self._key = self._credentials[0][1]
        self._preferred = 0
        self._rejected: set[int] = set()
        self.credential_slots_used: set[str] = set()

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        for wait_attempt in range(2):
            order = list(range(len(self._credentials)))
            preferred = self._preferred
            order.remove(preferred)
            failures = []
            for index in [preferred, *order]:
                if index in self._rejected:
                    continue
                name, key = self._credentials[index]
                try:
                    value = self._complete_with_key(messages, budget, key, wait_for_rate_limit=len(order) == 0)
                except ProviderError as exc:
                    if exc.status not in {401, 403, 429}:
                        raise
                    failures.append(exc)
                    if exc.status in {401, 403}:
                        self._rejected.add(index)
                    continue
                self._preferred = index
                self.credential_slots_used.add(name)
                return value
            limited = [exc for exc in failures if exc.status == 429]
            if not limited:
                raise failures[-1] if failures else ProviderError(self.model, 401)
            earliest = min(limited, key=lambda exc: exc.retry_after)
            if wait_attempt or len(order) == 0 or earliest.retry_after > 8:
                raise earliest
            time.sleep(earliest.retry_after + 0.1)
        raise AssertionError("unreachable")

    def payload(self, messages: list[dict], budget: int) -> dict:
        body = super().payload(messages, budget)
        body["max_completion_tokens"] = budget
        if body["model"].startswith("openai/gpt-oss-"):
            body["reasoning_effort"] = "low"
        return body


class Nvidia(HostedClient):
    key_variable = "NVIDIA_API_KEY"
    url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def payload(self, messages: list[dict], budget: int) -> dict:
        body = super().payload(messages, budget)
        return body | {"max_tokens": budget, "chat_template_kwargs": {"enable_thinking": False}}


class Cloudflare(ModelClient):
    """Cloudflare Workers AI via OpenAI-compatible REST API (free tier)."""

    key_variable = "CLOUDFLARE_API_TOKEN"
    account_variable = "CLOUDFLARE_ACCOUNT_ID"

    def __init__(self, model: str):
        self.model = model
        self._key = provider_key(self.key_variable)
        self._account = provider_key(self.account_variable)
        name = model.split(":", 1)[1]
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{self._account}/ai/v1/chat/completions"
        self._model_name = name

    def output_budget(self, stage: str, attempt: int) -> int:
        return min(1024, OUTPUT_BUDGET.get(stage, 320) * (attempt + 1))

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        body = {
            "model": self._model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": budget,
            "response_format": {"type": "json_object"},
        }
        provider = "Cloudflare"
        request = Request(self.url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json",
            "User-Agent": "ForgeAI/1.0",
            "Authorization": f"Bearer {self._key}",
        })
        data = provider_response(request, self.model, self._key, 60)
        if data.get("errors"):
            raise RuntimeError("Cloudflare returned an API error.")
        return data["choices"][0]["message"]["content"]


# Ordered fallback chain: each entry is a (prefix, class) pair.
# When a model string matches the prefix and that provider fails with a
# RuntimeError, the next provider in the chain is tried automatically.
_PROVIDER_CLASSES: dict[str, type[ModelClient]] = {
    "groq": Groq,
    "nvidia": Nvidia,
    "cloudflare": Cloudflare,
}

# Configurable fallback order: set FORGE_FALLBACK_PROVIDERS=groq,cloudflare,nvidia
# in the environment or .env to override the default.
_DEFAULT_FALLBACK = ["groq", "cloudflare", "nvidia"]


def _fallback_chain() -> list[str]:
    raw = os.getenv("FORGE_FALLBACK_PROVIDERS", "").strip()
    if not raw:
        path = Path.cwd() / ".env"
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, _, value = line.strip().removeprefix("export ").partition("=")
                if name.strip() == "FORGE_FALLBACK_PROVIDERS" and value.strip():
                    raw = value.strip().strip("\"'")
                    break
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip() in _PROVIDER_CLASSES]
    return _DEFAULT_FALLBACK


class FallbackClient(ModelClient):
    """Transparently retries the same call across a prioritised provider chain."""

    def __init__(self, model: str, chain: list[ModelClient]):
        self.model = model
        self._chain = chain
        self.models_used: set[str] = set()
        self.last_model = chain[0].model

    def output_budget(self, stage: str, attempt: int) -> int:
        return self._chain[0].output_budget(stage, attempt)

    def complete(self, messages: list[dict], schema: type[T], budget: int) -> str:
        last_exc: Exception | None = None
        for client in self._chain:
            try:
                result = client.complete(messages, schema, budget)
                if client is not self._chain[0]:
                    print(f"[ForgeAI] Fell back to {type(client).__name__} {client.model}", flush=True)
                self.last_model = client.model
                self.models_used.add(client.model)
                return result
            except (RuntimeError, URLError, TimeoutError) as exc:
                print(f"[ForgeAI] {type(client).__name__} failed: {exc}", flush=True)
                last_exc = exc
        if isinstance(last_exc, ProviderError):
            raise last_exc
        raise RuntimeError("All configured providers exhausted.") from last_exc

    def ask(self, stage: str, payload: dict, schema: type[T]) -> T:
        # Delegate to first client's ask(), which calls complete(), which we override.
        # We need to replicate the ask() logic so our complete() (with fallback) is used.
        import json as _json
        system = (PROMPTS / "boundary.txt").read_text() + "\n" + (PROMPTS / f"{stage}.txt").read_text()
        system += "\nResponse schema: " + _json.dumps(schema.model_json_schema())
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": _json.dumps(payload, ensure_ascii=False)}]
        for attempt in range(2):
            budget = self.output_budget(stage, attempt)
            try:
                return schema.model_validate_json(self.complete(messages, schema, budget))
            except (URLError, TimeoutError) as exc:
                raise RuntimeError(f"FallbackClient {self.model}: {exc}") from exc
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                if attempt:
                    raise ValueError(f"Invalid {stage} output after two attempts: {str(exc)[:400]}") from exc
                messages.append({"role": "user", "content": f"Correct the JSON for this validation error: {str(exc)[:400]}"})
        raise AssertionError("unreachable")


def make_model(model: str) -> ModelClient:
    if model.startswith("groq:"):
        return Groq(model)
    if model.startswith("nvidia:"):
        return Nvidia(model)
    if model.startswith("cloudflare:"):
        return Cloudflare(model)
    if model == "auto" or model.startswith("fallback:"):
        # Build a fallback chain from available providers
        base_model = model.split(":", 1)[1] if ":" in model else ""
        chain_providers = _fallback_chain()
        chain: list[ModelClient] = []
        for provider in chain_providers:
            cls = _PROVIDER_CLASSES[provider]
            # Choose a reasonable default model for each provider
            defaults = {
                "groq": GROQ_DEFAULT,
                "nvidia": "nvidia:nvidia/nemotron-3.5-lightning-30b-a3b",
                "cloudflare": "cloudflare:@cf/meta/llama-3.1-8b-instruct",
            }
            m = base_model if base_model else defaults.get(provider, "")
            if not m:
                continue
            try:
                chain.append(cls(m if ":" in m else f"{provider}:{m}"))
            except RuntimeError:
                pass  # Credential not configured; skip this provider
        if not chain:
            raise RuntimeError("No providers configured for fallback chain")
        return FallbackClient(model, chain)
    return Ollama(model)
