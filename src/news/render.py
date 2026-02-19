from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from rich.console import Console
from rich.table import Table

from .models import Cluster, NewsItem

console = Console(no_color=True)
MAX_ITEMS_PER_CLUSTER = 5


def set_color(enabled: bool) -> None:
    global console
    console = Console(no_color=not enabled)


def format_timestamp(dt: datetime | None) -> str:
    if not dt:
        return "(no timestamp)"
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%d %H:%M UTC")


def print_fetch_summary(items: Sequence[NewsItem], *, top_n: int = 5) -> None:
    count = len(items)
    console.print(f"[bold green]{count}[/bold green] new items", highlight=False)
    for item in items[:top_n]:
        timestamp = format_timestamp(item.published_dt)
        console.print(f" • [cyan]{item.title}[/cyan] — {item.source} ({timestamp})")


def print_clusters(clusters: Sequence[Cluster], *, max_items: int = MAX_ITEMS_PER_CLUSTER) -> None:
    if not clusters:
        console.print("No new clusters to summarize.")
        return
    for idx, cluster in enumerate(clusters, start=1):
        console.rule(f"Cluster {idx}: {cluster.headline()}")
        if cluster.summary:
            console.print(cluster.summary)
        if cluster.keywords:
            console.print(f"Keywords: {', '.join(cluster.keywords)}")
        sources = "; ".join(sorted({item.source for item in cluster.items}))
        if sources:
            console.print(f"Sources: {sources}")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Source")
        table.add_column("Title")
        table.add_column("Published")
        for item in cluster.items[:max_items]:
            table.add_row(item.source, item.title, format_timestamp(item.published_dt))
        console.print(table)
