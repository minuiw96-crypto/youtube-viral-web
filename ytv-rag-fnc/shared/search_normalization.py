"""Deterministic normalization and ranking for local lexical RAG search."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


SEARCH_STOPWORDS = {
    "그",
    "내",
    "우리",
    "이",
    "저",
    "영상",
    "채널",
    "알려줘",
    "보여줘",
    "설명",
    "설명해줘",
    "뭐야",
    "무엇",
    "무슨",
    "뜻",
    "값",
    "분석",
    "조회수",
    "점수",
    "shap",
}

KOREAN_PARTICLES = (
    "으로부터",
    "에서부터",
    "에게서는",
    "에서는",
    "으로는",
    "부터는",
    "까지는",
    "이라는",
    "이란",
    "이랑",
    "처럼",
    "보다",
    "부터",
    "까지",
    "에서",
    "으로",
    "로는",
    "과의",
    "와의",
    "에게",
    "한테",
    "께서",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "로",
    "와",
    "과",
    "도",
    "만",
)


def normalize_search_text(value: Any) -> str:
    """Normalize Unicode, case, separators, and punctuation into stable words."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    # Split a digit run from an adjacent Korean run (e.g. "연평도1편" -> "연평도 1편")
    # so a query typed without a space still tokenizes the same as a title with one.
    text = re.sub(r"(?<=[0-9])(?=[가-힣])|(?<=[가-힣])(?=[0-9])", " ", text)
    text = text.casefold()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return " ".join(text.split())


def _strip_korean_particle(token: str) -> str:
    if not re.fullmatch(r"[가-힣]+", token):
        return token
    for particle in KOREAN_PARTICLES:
        if token.endswith(particle) and len(token) - len(particle) >= 2:
            return token[: -len(particle)]
    return token


def search_tokens(value: Any) -> set[str]:
    """Return useful tokens, including Korean forms with a trailing particle removed."""
    tokens: set[str] = set()
    for token in normalize_search_text(value).split():
        if len(token) < 2 or token in SEARCH_STOPWORDS:
            continue
        tokens.add(token)
        stripped = _strip_korean_particle(token)
        if len(stripped) >= 2 and stripped not in SEARCH_STOPWORDS:
            tokens.add(stripped)
    return tokens


def content_tokens(value: Any) -> set[str]:
    """Particle-stripped tokens with no stopword filtering.

    search_tokens() drops domain words like "점수"/"조회수"/"영상" from the
    result because they're too generic to help rank search relevance. For
    near-duplicate detection (e.g. answer_policy's redundancy check) those are
    exactly the repeated words we need to compare, so this keeps them.
    """
    tokens: set[str] = set()
    for token in normalize_search_text(value).split():
        if len(token) < 2:
            continue
        tokens.add(_strip_korean_particle(token))
    return tokens


def _document_text(document: dict[str, Any], field: str) -> str:
    value = document.get(field)
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def lexical_rank_documents(
    question: str,
    documents: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Rank exact terms and aliases above incidental content-token matches."""
    limit = max(1, min(int(limit), 10))
    query_normalized = normalize_search_text(question)
    query_compact = query_normalized.replace(" ", "")
    query_tokens = search_tokens(question)
    if not query_compact:
        return []

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, document in enumerate(documents):
        title = _document_text(document, "title")
        aliases = document.get("aliases") or []
        if not isinstance(aliases, list):
            aliases = [aliases]
        phrases = [(title, 30), *((str(alias), 24) for alias in aliases)]

        score = 0
        for phrase, weight in phrases:
            normalized_phrase = normalize_search_text(phrase)
            compact_phrase = normalized_phrase.replace(" ", "")
            if len(compact_phrase) >= 2 and compact_phrase in query_compact:
                score += weight

        title_alias_text = f"{title} {' '.join(str(alias) for alias in aliases)}"
        title_alias_tokens = search_tokens(title_alias_text)
        content_tokens = search_tokens(_document_text(document, "content"))
        score += 4 * len(query_tokens & title_alias_tokens)
        score += len(query_tokens & content_tokens)

        if score > 0:
            ranked.append((score, index, document))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return []
    minimum_score = max(2, (ranked[0][0] + 3) // 4)
    return [
        document
        for score, _, document in ranked
        if score >= minimum_score
    ][:limit]
