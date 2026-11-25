import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).with_name("prompts")


class Ollama:
    def __init__(self, model: str):
        self.model = model
        self.url = os.getenv("FORGE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"

    def ask(self, stage: str, payload: dict, schema: type[T]) -> T:
        system = (PROMPTS / "boundary.txt").read_text() + "\n" + (PROMPTS / f"{stage}.txt").read_text()
        system += "\nResponse schema: " + json.dumps(schema.model_json_schema())
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        for attempt in range(2):
            body = dict(model=self.model, messages=messages, format=schema.model_json_schema(),
                        stream=False, options={"temperature": 0, "num_ctx": 4096, "num_predict": 640, "num_thread": 4})
            try:
                req = Request(self.url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=240) as response:
                    content = json.load(response)["message"]["content"]
                return schema.model_validate_json(content)
            except (URLError, TimeoutError) as exc:
                raise RuntimeError(f"Ollama {self.model} at {self.url}: {exc}") from exc
            except (ValueError, KeyError, TypeError) as exc:
                if attempt:
                    raise ValueError(f"Invalid {stage} output after two attempts: {exc}") from exc
                messages.append({"role": "user", "content": f"Correct the JSON for this validation error: {str(exc)[:400]}"})
        raise AssertionError("unreachable")

