from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from .models import Cluster

log = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


@dataclass(slots=True)
class OllamaConfig:
    base_url: str
    model: str
    timeout_s: int


class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self._base = config.base_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self._base}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            return any(m.get("name") == self.config.model for m in models) or bool(models)
        except requests.RequestException as exc:
            log.debug("Ollama availability check failed: %s", exc)
            return False

    def summarize_cluster(self, cluster: Cluster, *, max_items: int = 5) -> str:
        prompt = self._build_prompt(cluster, max_items=max_items)
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = requests.post(
                f"{self._base}/api/generate",
                json=payload,
                timeout=self.config.timeout_s,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        data = response.json()
        if "response" not in data:
            raise OllamaError("Malformed Ollama response")
        return data["response"].strip()

    @staticmethod
    def _build_prompt(cluster: Cluster, *, max_items: int) -> str:
        lines = [
            "Summarize the following related news items in 3 concise sentences.",
            "Highlight what is new and avoid repetition.",
            "Respond with markdown using one short paragraph and optional bullet list of takeaways.",
            "Stories:",
        ]
        for item in cluster.items[:max_items]:
            lines.append(f"- {item.title} (source: {item.source})")
            if item.summary:
                lines.append(f"  Summary: {item.summary[:280]}")
        return "\n".join(lines)


def build_client(config: OllamaConfig | None) -> OllamaClient | None:
    if not config:
        return None
    client = OllamaClient(config)
    if client.is_available():
        return client
    log.info("Ollama not available at %s", config.base_url)
    return None
