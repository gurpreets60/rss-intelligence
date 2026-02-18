from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import pytest

from news.models import NewsItem


@pytest.fixture
def make_item() -> Callable[..., NewsItem]:
    def _factory(**overrides) -> NewsItem:
        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        data = {
            "id": overrides.get("id", "item-1"),
            "title": overrides.get("title", "Sample Title"),
            "link": overrides.get("link", "https://example.com/a"),
            "source": overrides.get("source", "Example"),
            "published_dt": overrides.get("published_dt", base_time),
            "summary": overrides.get("summary", "Sample summary"),
            "content": overrides.get("content", None),
            "tags": list(overrides.get("tags", ["tech"])),
            "authors": list(overrides.get("authors", ["Reporter"])),
            "raw": overrides.get("raw"),
        }
        return NewsItem(**data)

    return _factory
