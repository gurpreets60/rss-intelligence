from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .models import Cluster, NewsItem


class CacheStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.cache_dir / "state.json"
        self._data = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {"seen_links": {}, "seen_clusters": {}}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return {"seen_links": {}, "seen_clusters": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))

    def has_seen(self, link: str) -> bool:
        return link in self._data["seen_links"]

    def mark_seen(self, link: str) -> None:
        self._data["seen_links"][link] = self._now()

    def filter_new_items(self, items: Sequence[NewsItem], *, mark: bool = False) -> list[NewsItem]:
        fresh: list[NewsItem] = []
        for item in items:
            if self.has_seen(item.link):
                continue
            fresh.append(item)
            if mark:
                self.mark_seen(item.link)
        if mark:
            self._save()
        return fresh

    def mark_items(self, items: Iterable[NewsItem]) -> None:
        changed = False
        for item in items:
            if item.link not in self._data["seen_links"]:
                self._data["seen_links"][item.link] = self._now()
                changed = True
        if changed:
            self._save()

    def mark_clusters(self, clusters: Iterable[Cluster]) -> None:
        changed = False
        for cluster in clusters:
            if cluster.id not in self._data["seen_clusters"]:
                self._data["seen_clusters"][cluster.id] = self._now()
                changed = True
        if changed:
            self._save()

    def unseen_clusters(self, clusters: Sequence[Cluster]) -> list[Cluster]:
        fresh = [cluster for cluster in clusters if cluster.id not in self._data["seen_clusters"]]
        return fresh

    @staticmethod
    def _now() -> str:
        return datetime.now(tz=timezone.utc).isoformat()
