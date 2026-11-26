"""Server-side client for the ForgeAI FastAPI service."""
import os
from urllib.parse import quote

import requests
import streamlit as st


class APIError(Exception):
    """An API request the user can retry or correct."""


def setting(name: str, default: str = "") -> str:
    if value := os.getenv(name):
        return value
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default


def endpoint(*segments: str) -> str:
    return "/api/" + "/".join(quote(segment, safe="") for segment in segments)


def request(path: str, *, timeout: int = 30, binary: bool = False, **kwargs):
    base = setting("FORGEAI_API_URL", "http://127.0.0.1:8000").rstrip("/")
    token = setting("FORGEAI_API_TOKEN")
    try:
        response = requests.request(
            "POST" if kwargs else "GET", base + path, timeout=(5, timeout),
            headers={"Authorization": f"Bearer {token}"} if token else {},
            allow_redirects=False, **kwargs,
        )
    except requests.RequestException as exc:
        raise APIError("Backend connection failed or timed out. Try again.") from exc
    if not response.ok or response.is_redirect:
        detail = f"Backend returned HTTP {response.status_code}."
        try:
            detail = response.json().get("detail") or detail
        except (ValueError, AttributeError):
            pass
        raise APIError(str(detail))
    if binary:
        return response.content
    try:
        return response.json()
    except ValueError as exc:
        raise APIError("Backend returned an invalid JSON response.") from exc
