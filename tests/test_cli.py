from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from news import cli
from news.models import Cluster, NewsItem
from news.summarize import PipelineResult

runner = CliRunner()


class DummyCache:
    def __init__(self, *_args, **_kwargs):
        self.seen: set[str] = set()

    def filter_new_items(self, items, mark=False):  # noqa: ARG002
        return [item for item in items if item.link not in self.seen]

    def mark_items(self, items):
        for item in items:
            self.seen.add(item.link)

    def mark_clusters(self, clusters):  # noqa: ARG002
        return None


def _write_config(tmp_path: Path) -> Path:
    config = tmp_path / "feeds.yaml"
    config.write_text(
        """
settings:
  cache_dir: .cache
  ollama:
    enabled: false
feeds:
  - name: Example
    url: https://example.com/rss
"""
    )
    return config


def _news_item(title: str, link: str) -> NewsItem:
    return NewsItem(id=link, title=title, link=link, source="Example")


def test_cli_fetch_reports_items(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    items = [_news_item("Story", "https://example.com/a"), _news_item("Story2", "https://example.com/b")]

    monkeypatch.setattr(cli, "fetch_all_feeds", lambda *args, **kwargs: items)
    monkeypatch.setattr(cli, "dedupe_items", lambda data: data)
    monkeypatch.setattr(cli, "apply_filters", lambda data, opts: data)
    monkeypatch.setattr(cli, "CacheStore", DummyCache)
    monkeypatch.setattr(cli, "print_fetch_summary", lambda data, top_n: print(f"{len(data)} shown"))

    result = runner.invoke(cli.app, ["fetch", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "2 shown" in result.stdout


def test_cli_fetch_since_option(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    items = [_news_item("Story", "https://example.com/a")]

    monkeypatch.setattr(cli, "fetch_all_feeds", lambda *args, **kwargs: items)
    monkeypatch.setattr(cli, "dedupe_items", lambda data: data)

    captured: dict[str, object] = {}

    def fake_apply_filters(data, opts):
        captured["since"] = opts.since
        return data

    monkeypatch.setattr(cli, "apply_filters", fake_apply_filters)
    monkeypatch.setattr(cli, "CacheStore", DummyCache)
    monkeypatch.setattr(cli, "print_fetch_summary", lambda data, top_n: None)
    sentinel = object()
    monkeypatch.setattr(cli, "build_since_from_cli", lambda value, settings: sentinel)

    result = runner.invoke(
        cli.app,
        [
            "fetch",
            "--config",
            str(config_path),
            "--since",
            "3d",
        ],
    )
    assert result.exit_code == 0
    assert captured.get("since") is sentinel


def test_cli_summarize_uses_pipeline(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    item = _news_item("Story", "https://example.com/a")
    cluster = Cluster(cluster_id="c1", items=[item], score=1.0, keywords=["story"], summary="Summary")
    pipeline_result = PipelineResult(clusters=[cluster], items=[item], llm_used=False)

    monkeypatch.setattr(cli, "run_pipeline", lambda *args, **kwargs: pipeline_result)
    monkeypatch.setattr(cli, "print_clusters", lambda clusters: print(f"clusters:{len(clusters)}"))

    result = runner.invoke(
        cli.app,
        [
            "summarize",
            "--config",
            str(config_path),
            "--include",
            "story",
            "--exclude",
            "skip",
            "--domain",
            "example.com",
            "--tag",
            "tech",
            "--threshold",
            "0.5",
            "--max-items",
            "10",
            "--no-llm",
        ],
    )
    assert result.exit_code == 0
    assert "clusters:1" in result.stdout
