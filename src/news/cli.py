from __future__ import annotations

import resource
import shutil
import sys
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
from .render import print_clusters, print_fetch_summary, set_color
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
    since: str | None = typer.Option(None, help="Recency window like 24h or 3d"),
    top: int | None = typer.Option(None, help="Show this many top titles"),
    include: list[str] | None = typer.Option(None, "--include", "-i", help="Keyword to include", show_default=False),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Keyword to exclude", show_default=False),
    domain: list[str] | None = typer.Option(None, "--domain", help="Only include host"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Only include feed tag"),
    color: bool = typer.Option(False, "--color/--no-color", help="Enable ANSI colors in output"),
) -> None:
    config, cache, _ = _setup(config_path)
    set_color(color)
    items = fetch_all_feeds(config.feeds, config.settings)
    deduped = dedupe_items(items)
    unseen = cache.filter_new_items(deduped, mark=False)
    since_dt = build_since_from_cli(since, config.settings)
    filtered = apply_filters(
        unseen,
        FilterOptions(
            since=since_dt,
            include=tuple(include or []),
            exclude=tuple(exclude or []),
            domains=tuple(domain or []),
            tags=tuple(tag or []),
        ),
    )
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
    color: bool = typer.Option(False, "--color/--no-color", help="Enable ANSI colors in output"),
) -> None:
    config, cache, _ = _setup(config_path)
    set_color(color)
    start = time.perf_counter()
    filter_opts = _build_filter_options(config, since, include, exclude, domain, tag, max_items)
    pipeline_opts = PipelineOptions(filters=filter_opts, threshold=threshold, max_items=max_items, llm_enabled=llm)
    client = _maybe_build_ollama(config, llm)
    result = run_pipeline(config, cache, pipeline_opts, llm=client)
    _render_result(result)
    _print_run_stats(time.perf_counter() - start)


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
    color: bool = typer.Option(False, "--color/--no-color", help="Enable ANSI colors in output"),
) -> None:
    config, cache, _ = _setup(config_path)
    set_color(color)
    interval_seconds = max(5, int(parse_duration(interval).total_seconds()))
    client = _maybe_build_ollama(config, llm)
    try:
        while True:
            start = time.perf_counter()
            filter_opts = _build_filter_options(config, since, include, exclude, domain, tag, max_items)
            pipeline_opts = PipelineOptions(filters=filter_opts, threshold=threshold, max_items=max_items, llm_enabled=llm)
            result = run_pipeline(config, cache, pipeline_opts, llm=client)
            _render_result(result)
            _print_run_stats(time.perf_counter() - start, prefix="[watch]")
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


def _print_run_stats(duration_s: float, prefix: str = "") -> None:
    memory_mb = _current_memory_mb()
    label = f"{prefix} " if prefix else ""
    typer.echo(f"{label}Completed in {duration_s:.2f}s | RSS ~{memory_mb:.1f} MB")


def _current_memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        usage /= 1024  # bytes -> KB
    return usage / 1024  # KB -> MB
