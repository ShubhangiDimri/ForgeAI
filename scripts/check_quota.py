"""Check API provider quota and connectivity."""
import json
import sys
import urllib.request
from pathlib import Path

# Resolve project root
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from forgeai.llm import provider_key


def check_groq():
    key = provider_key("GROQ_API_KEY")
    body = json.dumps({
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": '{"questions":[]}'}],
        "max_completion_tokens": 5,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "low",
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "ForgeAI/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            hdrs = dict(r.headers)
            print("Groq: OK")
    except urllib.request.HTTPError as exc:
        hdrs = dict(exc.headers)
        print(f"Groq: HTTP {exc.code}")
        exc.close()
    for k, v in hdrs.items():
        if "ratelimit" in k.lower() or "retry" in k.lower():
            print(f"  {k}: {v}")


def check_cloudflare():
    try:
        key = provider_key("CLOUDFLARE_API_TOKEN")
        account = provider_key("CLOUDFLARE_ACCOUNT_ID")
    except RuntimeError as exc:
        print(f"Cloudflare: not configured ({exc})")
        return
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/models/search?per_page=5",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "ForgeAI/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        count = len(data.get("result", []))
        print(f"Cloudflare: OK ({count} models in page)")
    except Exception as exc:
        print(f"Cloudflare: {exc}")


def check_nvidia():
    try:
        key = provider_key("NVIDIA_API_KEY")
    except RuntimeError as exc:
        print(f"NVIDIA: not configured ({exc})")
        return
    body = json.dumps({
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "messages": [{"role": "user", "content": '{"questions":[]}'}],
        "max_tokens": 5,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "ForgeAI/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            hdrs = dict(r.headers)
            print("NVIDIA: OK")
    except urllib.request.HTTPError as exc:
        print(f"NVIDIA: HTTP {exc.code}")
        exc.close()


if __name__ == "__main__":
    check_groq()
    check_cloudflare()
    check_nvidia()

