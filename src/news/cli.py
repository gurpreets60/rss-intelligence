from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Iterable

import subprocess

import typer

from .cache import CacheStore
from .config import AppConfig, build_since_from_cli, load_config, parse_duration
from .dedupe import dedupe_items
from .feeds import fetch_all_feeds
from .filter import apply_filters
from .models import FilterOptions, PipelineOptions
from .ollama_client import OllamaClient, OllamaConfig, build_client
from .render import print_clusters, print_fetch_summary
from .summarize import PipelineResult, run_pipeline

app = typer.Typer(help="RSS Intelligence CLI")


def _setup(config_path: Path) -> tuple[AppConfig, CacheStore, Path]:
    result = load_config(config_path)
    base_dir = result.path.parent
    cache_dir = result.config.ensure_cache_dir(base_dir)
    cache = CacheStore(cache_dir)
    return result.config, cache, base_dir


@app.command()
def fetch(
    config_path: Path = typer.Option(Path("feeds.yaml"), "--config", help="Path to feeds YAML"),
    top: int | None = typer.Option(None, help="Show this many top titles"),
) -> None:
    config, cache, _ = _setup(config_path)
    items = fetch_all_feeds(config.feeds, config.settings)
    deduped = dedupe_items(items)
    unseen = cache.filter_new_items(deduped, mark=False)
    since = build_since_from_cli(None, config.settings)
    filtered = apply_filters(unseen, FilterOptions(since=since))
    cache.mark_items(filtered)
    top_n = top or config.settings.top_n_fetch
    print_fetch_summary(filtered, top_n=top_n)


@app.command()
def summarize(
    config_path: Path = typer.Option(Path("feeds.yaml"), "--config", help="Path to feeds YAML"),
    since: str | None = typer.Option(None, help="Recency window like 24h or 3d"),
    include: list[str] | None = typer.Option(None, "--include", "-i", help="Keyword to include", show_default=False),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Keyword to exclude", show_default=False),
    domain: list[str] | None = typer.Option(None, "--domain", help="Only include host"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Only include feed tag"),
    threshold: float = typer.Option(0.55, help="Clustering similarity threshold (0-1)"),
    max_items: int | None = typer.Option(None, help="Cap number of items processed"),
    llm: bool = typer.Option(True, "--llm/--no-llm", help="Toggle Ollama summarization"),
) -> None:
    config, cache, _ = _setup(config_path)
    filter_opts = _build_filter_options(config, since, include, exclude, domain, tag, max_items)
    pipeline_opts = PipelineOptions(filters=filter_opts, threshold=threshold, max_items=max_items, llm_enabled=llm)
    client = _maybe_build_ollama(config, llm)
    result = run_pipeline(config, cache, pipeline_opts, llm=client)
    _render_result(result)


@app.command()
def watch(
    config_path: Path = typer.Option(Path("feeds.yaml"), "--config", help="Path to feeds YAML"),
    interval: str = typer.Option("30m", help="Refresh interval"),
    since: str | None = typer.Option(None, help="Recency window like 24h or 3d"),
    include: list[str] | None = typer.Option(None, "--include", "-i", help="Keyword to include", show_default=False),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Keyword to exclude", show_default=False),
    domain: list[str] | None = typer.Option(None, "--domain", help="Only include host"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Only include feed tag"),
    threshold: float = typer.Option(0.55, help="Clustering similarity threshold (0-1)"),
    max_items: int | None = typer.Option(None, help="Cap number of items processed"),
    llm: bool = typer.Option(True, "--llm/--no-llm", help="Toggle Ollama summarization"),
    notify: bool = typer.Option(False, "--notify", help="Use notify-send when available"),
) -> None:
    config, cache, _ = _setup(config_path)
    interval_seconds = max(5, int(parse_duration(interval).total_seconds()))
    client = _maybe_build_ollama(config, llm)
    try:
        while True:
            filter_opts = _build_filter_options(config, since, include, exclude, domain, tag, max_items)
            pipeline_opts = PipelineOptions(filters=filter_opts, threshold=threshold, max_items=max_items, llm_enabled=llm)
            result = run_pipeline(config, cache, pipeline_opts, llm=client)
            _render_result(result)
            if notify and result.clusters:
                _notify(f"{len(result.clusters)} new clusters")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        typer.echo("Stopping watch mode...")


def _build_filter_options(
    config: AppConfig,
    since: str | None,
    include: Iterable[str] | None,
    exclude: Iterable[str] | None,
    domain: Iterable[str] | None,
    tag: Iterable[str] | None,
    max_items: int | None,
) -> FilterOptions:
    since_dt = build_since_from_cli(since, config.settings)
    return FilterOptions(
        since=since_dt,
        include=tuple(include or []),
        exclude=tuple(exclude or []),
        domains=tuple(domain or []),
        tags=tuple(tag or []),
        max_items=max_items,
    )


def _maybe_build_ollama(config: AppConfig, llm_flag: bool) -> OllamaClient | None:
    settings = config.settings.ollama
    if not (llm_flag and settings.enabled):
        return None
    ollama_config = OllamaConfig(
        base_url=settings.base_url,
        model=settings.model,
        timeout_s=settings.timeout_s,
    )
    return build_client(ollama_config)


def _render_result(result: PipelineResult) -> None:
    if not result.items:
        typer.echo("No new items to process.")
        return
    print_clusters(result.clusters)


def _notify(message: str) -> None:
    binary = shutil.which("notify-send")
    if binary:
        subprocess.run([binary, "RSS Intel", message], check=False)
    else:
        typer.echo(f"[notify] {message}")
