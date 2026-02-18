from __future__ import annotations

from collections import Counter
from math import sqrt
from typing import Sequence

from .models import Cluster, NewsItem, newest_first

_TOKEN_DELIMS = "\t\n\r .,;:!?()[]{}<>\"'"


def cluster_items(
    items: Sequence[NewsItem],
    *,
    similarity_threshold: float = 0.55,
    max_items: int | None = None,
) -> list[Cluster]:
    ordered = newest_first(items)
    if max_items is not None:
        ordered = ordered[:max_items]

    clusters: list[Cluster] = []
    vectors: list[Counter[str]] = []

    for item in ordered:
        item_vector = _vectorize_item(item)
        assigned = False
        for idx, vector in enumerate(vectors):
            score = _cosine_similarity(item_vector, vector)
            if score >= similarity_threshold:
                clusters[idx].items.append(item)
                clusters[idx].score = max(clusters[idx].score, score)
                vector.update(item_vector)
                assigned = True
                break
        if not assigned:
            cluster_id = f"cluster-{len(clusters) + 1}"
            clusters.append(
                Cluster(
                    id=cluster_id,
                    items=[item],
                    score=1.0,
                    top_keywords=(),
                    summary=None,
                )
            )
            vectors.append(item_vector)

    for cluster, vector in zip(clusters, vectors):
        cluster.top_keywords = _top_keywords(vector, k=5)
        cluster.score = float(len(cluster.items))
    return clusters


def _vectorize_item(item: NewsItem) -> Counter[str]:
    text_parts = [item.title, item.summary or "", item.content or ""]
    tokens = _tokenize(" \n".join(text_parts))
    return Counter(tokens)


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    for delim in _TOKEN_DELIMS:
        text = text.replace(delim, " ")
    return [token for token in text.split() if len(token) > 2]


def _cosine_similarity(vec_a: Counter[str], vec_b: Counter[str]) -> float:
    intersection = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[token] * vec_b[token] for token in intersection)
    if dot == 0:
        return 0.0
    mag_a = sqrt(sum(value * value for value in vec_a.values()))
    mag_b = sqrt(sum(value * value for value in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _top_keywords(vector: Counter[str], k: int = 5) -> tuple[str, ...]:
    most_common = vector.most_common(k)
    return tuple(word for word, _ in most_common)
