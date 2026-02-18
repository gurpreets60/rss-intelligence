from __future__ import annotations

from news.cluster import cluster_items


def test_cluster_groups_similar_items(make_item):
    items = [
        make_item(id="1", title="AI chip launches", summary="Nvidia unveils new ai chip"),
        make_item(id="2", title="Nvidia releases AI chip", summary="Chip launch"),
        make_item(id="3", title="Global economy outlook", summary="IMF update"),
    ]
    clusters = cluster_items(items, similarity_threshold=0.3)
    assert len(clusters) == 2
    assert len(clusters[0].items) == 2
    assert clusters[0].top_keywords
