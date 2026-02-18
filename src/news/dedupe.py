from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Sequence
from urllib.parse import urlparse

from .models import NewsItem

STOPWORDS = {
    "the",
    "a",
    "an",
    "to",
    "and",
    "of",
    "in",
    "for",
    "on",
}


def dedupe_items(items: Sequence[NewsItem], *, title_threshold: float = 0.92) -> list[NewsItem]:
    seen_links: set[str] = set()
    normalized_titles: list[str] = []
    unique: list[NewsItem] = []
    for item in items:
        link_key = _normalize_link(item.link)
        if link_key and link_key in seen_links:
            continue
        norm_title = _normalize_title(item.title)
        if _has_similar_title(norm_title, normalized_titles, title_threshold):
            continue
        if link_key:
            seen_links.add(link_key)
        normalized_titles.append(norm_title)
        unique.append(item)
    return unique


def _normalize_link(link: str) -> str:
    parsed = urlparse(link)
    netloc = (parsed.hostname or parsed.netloc or "").lower()
    path = parsed.path.rstrip("/")
    if not netloc:
        return ""
    return f"{netloc}{path}"


def _normalize_title(title: str) -> str:
    tokens = re.split(r"[^a-zA-Z0-9]+", title.lower())
    cleaned: list[str] = []
    for token in tokens:
        if not token or token in STOPWORDS:
            continue
        if token.endswith("s") and len(token) > 3:
            token = token[:-1]
        cleaned.append(token)
    cleaned.sort()
    return " ".join(cleaned)


def _has_similar_title(reference: str, past_titles: Iterable[str], threshold: float) -> bool:
    return any(SequenceMatcher(a=reference, b=prev).ratio() >= threshold for prev in past_titles)
