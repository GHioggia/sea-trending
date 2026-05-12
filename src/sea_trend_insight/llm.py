"""Thin LLM client — OpenAI-compatible API (DeepSeek, etc.)."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

log = logging.getLogger("sea_trend_insight")


def _api_key(cfg: dict) -> str | None:
    return os.environ.get(cfg.get("api_key_env", "DEEPSEEK_API_KEY"))


def call(messages: list[dict[str, str]], cfg: dict, temperature: float = 0.3) -> str:
    api_key = _api_key(cfg)
    if not api_key:
        raise ValueError(f"API key not set (env var: {cfg.get('api_key_env', 'DEEPSEEK_API_KEY')})")

    base_url = cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
    model = cfg.get("model", "deepseek-chat")

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_json(messages: list[dict[str, str]], cfg: dict, temperature: float = 0.3) -> Any:
    raw = call(messages, cfg, temperature)
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text.strip())
    return json.loads(text.strip())
