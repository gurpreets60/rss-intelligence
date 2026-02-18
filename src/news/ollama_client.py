from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from .models import Cluster, NewsItem

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

    def summarize_cluster(self, cluster: Cluster, items: list[NewsItem], *, max_items: int = 5) -> str:
        prompt = self._build_prompt(cluster, items, max_items=max_items)
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
    def _build_prompt(cluster: Cluster, items: list[NewsItem], *, max_items: int) -> str:
        lines = [
            "You are drafting a newsroom digest from multiple sources.",
            "Write output exactly in this format:",
            "What happened: <single sentence summary>",
            "- <bullet 1>",
            "- <bullet 2>",
            "- <bullet 3>",
            "(add up to 6 bullets total)",
            "Sources: name1; name2; ...",
            "Bullets must highlight key entities, numbers, or dates when present.",
            "Use only the evidence provided; avoid speculation.",
            "Stories:",
        ]
        for item in items[:max_items]:
            summary = (item.summary or "")[:400].strip()
            lines.append(f"- {item.title} (source: {item.source})")
            if item.summary:
                lines.append(f"  Summary: {summary}")
            lines.append(f"  Link: {item.link}")
        return "\n".join(lines)


def build_client(config: OllamaConfig | None) -> OllamaClient | None:
    if not config:
        return None
    client = OllamaClient(config)
    if client.is_available():
        return client
    log.info("Ollama not available at %s", config.base_url)
    return None
