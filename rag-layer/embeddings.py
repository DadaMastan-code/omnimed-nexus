"""Shared embedding model — lazily loaded, cached as a singleton."""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    model = get_embedding_model(model_name)
    return model.encode(texts, show_progress_bar=False).tolist()
