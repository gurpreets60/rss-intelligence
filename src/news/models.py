from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(slots=True)
class NewsItem:
    """Normalized representation of a feed entry."""

    id: str
    title: str
    link: str
    source: str
    published_dt: datetime | None = None
    summary: str | None = None
    content: str | None = None
    tags: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None

    def text_blob(self) -> str:
        """Aggregate fields for keyword matching."""
        parts: list[str] = [self.title]
        if self.summary:
            parts.append(self.summary)
        if self.content and self.content not in parts:
            parts.append(self.content)
        return "\n".join(parts).strip()


@dataclass(slots=True)
class Cluster:
    cluster_id: str
    items: list[NewsItem]
    keywords: list[str] = field(default_factory=list)
    score: float | None = None
    summary: str | None = None

    @property
    def primary(self) -> NewsItem:
        return self.items[0]

    def headline(self) -> str:
        return self.primary.title

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.cluster_id,
            "score": self.score,
            "summary": self.summary,
            "keywords": self.keywords,
            "items": [item.__dict__ for item in self.items],
        }


@dataclass(slots=True)
class FilterOptions:
    since: datetime | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    max_items: int | None = None

    def normalized(self) -> "FilterOptions":
        def _to_tuple(values: Iterable[str]) -> tuple[str, ...]:
            return tuple(sorted({v.lower() for v in values if v}))

        return FilterOptions(
            since=self.since,
            include=_to_tuple(self.include),
            exclude=_to_tuple(self.exclude),
            domains=_to_tuple(self.domains),
            tags=_to_tuple(self.tags),
            max_items=self.max_items,
        )


@dataclass(slots=True)
class PipelineOptions:
    filters: FilterOptions = field(default_factory=FilterOptions)
    threshold: float = 0.55
    max_items: int | None = None
    llm_enabled: bool = True

    def clamp(self) -> "PipelineOptions":
        threshold = min(max(self.threshold, 0.0), 1.0)
        return PipelineOptions(
            filters=self.filters.normalized(),
            threshold=threshold,
            max_items=self.max_items,
            llm_enabled=self.llm_enabled,
        )


def newest_first(items: Sequence[NewsItem]) -> list[NewsItem]:
    return sorted(
        items,
        key=lambda item: item.published_dt or utc_now(),
        reverse=True,
    )
