import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).with_name("prompts")
OUTPUT_BUDGET = {"questions": 160, "requirements": 320, "coverage": 180, "design": 320,
                 "route": 150, "answer": 240, "eval_generate": 260, "eval_questions": 220, "eval_outside": 160, "eval_validate": 72, "judge": 160}


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
                raise RuntimeError(f"{type(self).__name__} {self.model} at {self.url}: {exc}") from exc
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


def provider_key(variable: str) -> str:
    """Read one provider credential from the environment or the project-root .env."""
    if value := os.getenv(variable, "").strip():
        return value
    path = Path.cwd() / ".env"
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
        body = self.payload(messages, budget)
        provider = type(self).__name__
        request = Request(self.url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "User-Agent": "ForgeAI/1.0",
            "Authorization": f"Bearer {self._key}"})
        for attempt in range(6):
            try:
                with urlopen(request, timeout=45) as response:
                    return json.load(response)["choices"][0]["message"]["content"]
            except HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After", "")
                exc.close()
                if status == 400:
                    raise ValueError(f"{provider} rejected the request or could not produce JSON") from None
                if attempt == 5 or status not in {429, 500, 502, 503, 504}:
                    raise RuntimeError(f"{provider} {body['model']} returned HTTP {status}") from None
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = 0
                if status == 429 and delay > 65:
                    raise RuntimeError(f"{provider} {body['model']} returned HTTP 429. Retry after {delay:g} seconds.") from None
                minimum = min(40, 4 * 2 ** attempt) if status == 429 else 2 ** attempt
                time.sleep(min(65, max(minimum, delay)))


class Groq(HostedClient):
    key_variable = "GROQ_API_KEY"
    url = "https://api.groq.com/openai/v1/chat/completions"

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


def make_model(model: str) -> ModelClient:
    if model.startswith("groq:"):
        return Groq(model)
    if model.startswith("nvidia:"):
        return Nvidia(model)
    return Ollama(model)
