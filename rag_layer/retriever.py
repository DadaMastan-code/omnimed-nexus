"""Unified retriever over the omnimed_knowledge Qdrant collection."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from config import settings
from rag_layer.embeddings import embed
from rag_layer.indexer import COLLECTION_NAME


def retrieve(
    query: str,
    sources: list[str] | None = None,
    top_k: int = 5,
    score_threshold: float = 0.4,
) -> list[dict[str, Any]]:
    """Retrieve relevant chunks from the knowledge base.

    Args:
        query: Natural-language query.
        sources: Filter by source labels ("codesense", "medfusion", "medbrain").
        top_k: Number of results.
        score_threshold: Minimum cosine similarity to include.

    Returns:
        List of dicts with keys: score, source, path, text, metadata.
    """
    client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
    )

    vector = embed([query])[0]

    query_filter = None
    if sources:
        query_filter = Filter(
            must=[FieldCondition(key="source", match=MatchAny(any=sources))]
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
        score_threshold=score_threshold,
    )

    return [
        {
            "score": round(r.score, 4),
            "source": r.payload.get("source"),
            "path": r.payload.get("path"),
            "text": r.payload.get("text"),
            "metadata": r.payload.get("metadata", {}),
        }
        for r in results
    ]


def format_context(results: list[dict[str, Any]]) -> str:
    """Format retrieval results as a context block for LLM injection."""
    if not results:
        return "No relevant context found."
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] Source: {r['source']} | File: {r['path']} | Score: {r['score']}")
        lines.append(r["text"])
        lines.append("")
    return "\n".join(lines)
