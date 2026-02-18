from __future__ import annotations

from typing import Sequence

from rich.console import Console
from rich.table import Table

from .models import Cluster, NewsItem

console = Console()


def print_fetch_summary(items: Sequence[NewsItem], *, top_n: int = 5) -> None:
    count = len(items)
    console.print(f"[bold green]{count}[/bold green] new items", highlight=False)
    for item in items[:top_n]:
        console.print(f" • [cyan]{item.title}[/cyan] — {item.source}")


def print_clusters(clusters: Sequence[Cluster]) -> None:
    if not clusters:
        console.print("No new clusters to summarize.")
        return
    for idx, cluster in enumerate(clusters, start=1):
        console.rule(f"Cluster {idx}: {cluster.headline()}")
        if cluster.summary:
            console.print(cluster.summary)
        if cluster.top_keywords:
            console.print(f"Keywords: {', '.join(cluster.top_keywords)}")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Source")
        table.add_column("Title")
        for item in cluster.items:
            table.add_row(item.source, item.title)
        console.print(table)
