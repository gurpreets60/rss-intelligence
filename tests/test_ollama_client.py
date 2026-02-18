from __future__ import annotations

import pytest
import requests

from news.models import Cluster
from news.ollama_client import OllamaClient, OllamaConfig, OllamaError


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_is_available(monkeypatch):
    def fake_get(url, timeout):  # noqa: ARG001
        return DummyResponse({"models": [{"name": "phi3"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    client = OllamaClient(OllamaConfig(base_url="http://localhost:11434", model="phi3", timeout_s=10))
    assert client.is_available()


def test_summarize_cluster(monkeypatch, make_item):
    def fake_post(url, json, timeout):  # noqa: ARG001
        assert json["model"] == "phi3"
        return DummyResponse({"response": "Summary content"})

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaClient(OllamaConfig(base_url="http://localhost:11434", model="phi3", timeout_s=10))
    cluster = Cluster(cluster_id="c1", items=[make_item()], score=1.0)
    summary = client.summarize_cluster(cluster)
    assert summary == "Summary content"


def test_summarize_cluster_handles_missing_response(monkeypatch, make_item):
    def fake_post(url, json, timeout):  # noqa: ARG001
        return DummyResponse({})

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaClient(OllamaConfig(base_url="http://localhost:11434", model="phi3", timeout_s=10))
    cluster = Cluster(cluster_id="c1", items=[make_item()], score=1.0)
    with pytest.raises(OllamaError):
        client.summarize_cluster(cluster)
