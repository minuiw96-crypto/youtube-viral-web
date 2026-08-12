"""Small-corpus cosine similarity search for embeddings stored in Cosmos DB."""

from __future__ import annotations

from math import sqrt
from typing import Any


def cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if not left or len(left) != len(right):
        return None
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)


def rank_documents(
    query_embedding: list[float],
    documents: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 10))
    ranked: list[tuple[float, dict[str, Any]]] = []
    for document in documents:
        vector = document.get("contentVector")
        if not isinstance(vector, list):
            continue
        try:
            similarity = cosine_similarity(
                [float(value) for value in query_embedding],
                [float(value) for value in vector],
            )
        except (TypeError, ValueError):
            continue
        if similarity is not None:
            ranked.append((similarity, document))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            key: value
            for key, value in document.items()
            if key not in {"contentVector", "_rid", "_self", "_etag", "_attachments", "_ts"}
        }
        | {"similarity": round(similarity, 6)}
        for similarity, document in ranked[:limit]
    ]
