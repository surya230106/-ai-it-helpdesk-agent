"""Optional Ollama provider. The deterministic diagnostic engine remains the fallback."""
from __future__ import annotations

import logging
import json
import re
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("helpdesk.llm")


def _safe_error_body(response: httpx.Response, messages: list[dict]) -> str:
    """Return a bounded Ollama error without echoing user content or credentials."""
    try:
        payload = response.json()
        body = payload.get("error", "") if isinstance(payload, dict) else ""
    except (ValueError, json.JSONDecodeError):
        body = "non-JSON error response"
    body = str(body or "empty error response")
    for message in messages:
        content = message.get("content")
        if isinstance(content, str) and len(content) >= 4:
            body = body.replace(content, "[redacted user/model content]")
    body = re.sub(r"(?i)\b(password|passcode|token|api[_ -]?key|secret|mfa)\s*[:=]\s*[^\s,;]+", r"\1=[redacted]", body)
    body = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted email]", body, flags=re.I)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:800]

class OllamaProvider:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_chat_model
        self.timeout = timeout or settings.ollama_timeout_seconds

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False, "think": False, "options": {"temperature": 0.2}}
        if tools:
            payload["tools"] = tools
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in (1, 2):
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                try:
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError:
                    safe_body = _safe_error_body(response, messages)
                    roles = [message.get("role", "unknown") for message in messages]
                    logger.error(
                        "ollama_chat_http_error status_code=%s response_body=%r endpoint=/api/chat model=%s "
                        "tools_included=%s tool_count=%s message_roles=%s attempt=%s",
                        response.status_code,
                        safe_body,
                        self.model,
                        bool(tools),
                        len(tools or []),
                        roles,
                        attempt,
                    )
                    runner_terminated = "llama-server process has terminated" in safe_body.lower()
                    if attempt == 1 and response.status_code >= 500 and runner_terminated:
                        logger.warning("ollama_chat_retrying_after_runner_exit model=%s endpoint=/api/chat", self.model)
                        time.sleep(0.5)
                        continue
                    raise
            body = response.json()
        message = body.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama returned an invalid chat response")
        return message

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/embed", json={"model": settings.ollama_embedding_model, "input": texts})
            response.raise_for_status()
            vectors = response.json().get("embeddings", [])
        return vectors if isinstance(vectors, list) and len(vectors) == len(texts) else []

    def health(self) -> dict:
        try:
            with httpx.Client(timeout=min(self.timeout, 2.0)) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
            names = [model.get("name", "") for model in models]
            return {"reachable": True, "model": self.model, "model_available": any(name == self.model or name.startswith(self.model + ":") for name in names)}
        except Exception as exc:
            logger.warning("ollama_health_failed error_type=%s", type(exc).__name__)
            return {"reachable": False, "model": self.model, "model_available": False}

def configured_provider() -> OllamaProvider | None:
    if settings.ai_mode.lower() == "local" and settings.ai_provider.lower() == "ollama":
        return OllamaProvider()
    return None
