"""Indexes GitHub repo content into the unified Qdrant knowledge base."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

import httpx
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import settings
from rag_layer.embeddings import embed

log = structlog.get_logger()

COLLECTION_NAME = "omnimed_knowledge"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2

SOURCE_MAP = {
    settings.codesense_repo: "codesense",
    settings.medfusion_repo: "medfusion",
    settings.medbrain_repo: "medbrain",
}

_http = httpx.AsyncClient(timeout=30.0)


def _get_client() -> QdrantClient:
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
    )


def ensure_collection() -> None:
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        log.info("qdrant_collection_created", name=COLLECTION_NAME)


async def _fetch_repo_files(repo: str, token: str) -> list[dict[str, Any]]:
    """Fetch Python/MD/TS files from GitHub via API (default branch)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    tree_resp = await _http.get(
        f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1",
        headers=headers,
    )
    if tree_resp.status_code != 200:
        log.warning("repo_tree_fetch_failed", repo=repo, status=tree_resp.status_code)
        return []

    tree = tree_resp.json().get("tree", [])
    text_files = [
        item for item in tree
        if item["type"] == "blob"
        and re.search(r"\.(py|md|ts|tsx|yml|yaml)$", item["path"])
        and item.get("size", 0) < 100_000  # skip large files
    ]

    documents: list[dict[str, Any]] = []
    for item in text_files[:200]:  # cap at 200 files per repo
        blob_resp = await _http.get(item["url"], headers={**headers, "Accept": "application/vnd.github.raw"})
        if blob_resp.status_code == 200:
            documents.append({
                "path": item["path"],
                "content": blob_resp.text,
            })

    return documents


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + chunk_size]))
        i += chunk_size - overlap
    return chunks


async def index_repo(repo: str) -> None:
    """Fetch all text files from `repo` and upsert chunks into Qdrant."""
    source_label = SOURCE_MAP.get(repo, repo.split("/")[-1])
    ensure_collection()

    files = await _fetch_repo_files(repo, settings.github_token)
    if not files:
        log.warning("index_repo_no_files", repo=repo)
        return

    client = _get_client()
    points: list[PointStruct] = []

    for doc in files:
        chunks = _chunk_text(doc["content"])
        vectors = embed(chunks)
        for chunk, vector in zip(chunks, vectors):
            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "source": source_label,
                        "repo": repo,
                        "path": doc["path"],
                        "text": chunk,
                        "metadata": {"file": doc["path"]},
                    },
                )
            )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    log.info("index_repo_complete", repo=repo, chunks=len(points))


async def index_all_repos() -> None:
    for repo in settings.all_repos:
        log.info("indexing_repo", repo=repo)
        await index_repo(repo)
