"""Tool definitions for the meta-agent — one tool per downstream system plus shared infra tools."""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from langchain_core.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from neo4j import GraphDatabase

from config import settings

log = structlog.get_logger()

_http = httpx.AsyncClient(timeout=60.0)


# ── codesense-ai ─────────────────────────────────────────────────────────────

@tool
async def review_code(code: str, language: str = "python", context: str = "") -> dict[str, Any]:
    """Submit code to codesense-ai for multi-agent review.

    Returns structured review: security, performance, architecture, tests, docs scores + issues.
    """
    try:
        resp = await _http.post(
            f"{settings.codesense_api_url}/review",
            json={"code": code, "language": language, "context": context},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("codesense_api_error", error=str(e))
        return {"error": str(e), "source": "codesense-ai"}


@tool
async def review_pr_diff(repo: str, pr_number: int) -> dict[str, Any]:
    """Trigger codesense-ai review on a specific GitHub PR diff."""
    try:
        resp = await _http.post(
            f"{settings.codesense_api_url}/review/pr",
            json={"repo": repo, "pr_number": pr_number, "github_token": settings.github_token},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("codesense_pr_review_error", repo=repo, pr=pr_number, error=str(e))
        return {"error": str(e), "source": "codesense-ai"}


# ── MedFusion-Leuk ───────────────────────────────────────────────────────────

@tool
async def diagnose_leukemia(
    image_path: str | None = None,
    cbc_data: dict[str, float] | None = None,
    patient_context: str = "",
) -> dict[str, Any]:
    """Submit a case to MedFusion-Leuk for multimodal leukemia diagnosis.

    Accepts microscopy image path and/or CBC lab values.
    Returns: classification, confidence, SHAP explanation, Grad-CAM heatmap URL.
    """
    payload: dict[str, Any] = {"patient_context": patient_context}
    if image_path:
        payload["image_path"] = image_path
    if cbc_data:
        payload["cbc_data"] = cbc_data

    try:
        resp = await _http.post(f"{settings.medfusion_api_url}/diagnose", json=payload)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("medfusion_api_error", error=str(e))
        return {"error": str(e), "source": "MedFusion-Leuk"}


@tool
async def explain_diagnosis(case_id: str) -> dict[str, Any]:
    """Retrieve SHAP + Grad-CAM XAI explanation for a MedFusion-Leuk diagnosis."""
    try:
        resp = await _http.get(f"{settings.medfusion_api_url}/explain/{case_id}")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "source": "MedFusion-Leuk"}


# ── medbrain-ai ──────────────────────────────────────────────────────────────

@tool
async def clinical_reason(
    query: str,
    patient_context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Submit a clinical reasoning query to medbrain-ai.

    Uses LangGraph multi-agent reasoning + Qdrant RAG + Neo4j long-term memory.
    Returns: reasoning chain, differential diagnoses, treatment suggestions, citations.
    """
    try:
        resp = await _http.post(
            f"{settings.medbrain_api_url}/reason",
            json={
                "query": query,
                "patient_context": patient_context or {},
                "session_id": session_id,
            },
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("medbrain_api_error", error=str(e))
        return {"error": str(e), "source": "medbrain-ai"}


@tool
async def recall_patient(patient_id: str) -> dict[str, Any]:
    """Retrieve a patient's full history from medbrain-ai's Neo4j memory graph."""
    try:
        resp = await _http.get(f"{settings.medbrain_api_url}/patient/{patient_id}")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "source": "medbrain-ai"}


# ── Unified RAG (Qdrant) ─────────────────────────────────────────────────────

@tool
async def search_knowledge(
    query: str,
    sources: list[str] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search the unified Qdrant knowledge base across all three repos.

    sources: filter by ["codesense", "medfusion", "medbrain"] or None for all.
    Returns ranked documents with source attribution.
    """
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vector = model.encode(query).tolist()

    query_filter = None
    if sources:
        query_filter = Filter(
            must=[FieldCondition(key="source", match=MatchAny(any=sources))]
        )

    results = client.search(
        collection_name="omnimed_knowledge",
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
    )

    return [
        {
            "score": r.score,
            "source": r.payload.get("source"),
            "text": r.payload.get("text"),
            "metadata": r.payload.get("metadata", {}),
        }
        for r in results
    ]


# ── Knowledge Graph (Neo4j) ──────────────────────────────────────────────────

@tool
def query_knowledge_graph(cypher: str) -> list[dict[str, Any]]:
    """Execute a read-only Cypher query against the omnimed-nexus Neo4j knowledge graph.

    Schema nodes: (Concept), (Patient), (Diagnosis), (CodeModule), (Model), (Finding)
    """
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    with driver.session() as session:
        result = session.run(cypher)
        return [dict(r) for r in result]


# ── GitHub ───────────────────────────────────────────────────────────────────

@tool
async def create_github_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a GitHub Issue in any of the monitored repositories."""
    headers = {"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json"}
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    try:
        resp = await _http.post(
            f"https://api.github.com/repos/{repo}/issues",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"url": data["html_url"], "number": data["number"]}
    except httpx.HTTPError as e:
        return {"error": str(e)}


@tool
async def get_repo_status(repo: str) -> dict[str, Any]:
    """Get health summary for a monitored GitHub repo: open issues, PRs, last commit, CI status."""
    headers = {"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient() as client:
            repo_resp, issues_resp, prs_resp = await asyncio.gather(
                client.get(f"https://api.github.com/repos/{repo}", headers=headers),
                client.get(f"https://api.github.com/repos/{repo}/issues?state=open&per_page=1", headers=headers),
                client.get(f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=1", headers=headers),
            )
        r = repo_resp.json()
        return {
            "repo": repo,
            "stars": r.get("stargazers_count"),
            "open_issues": r.get("open_issues_count"),
            "open_prs": int(prs_resp.headers.get("x-total-count", 0)),
            "default_branch": r.get("default_branch"),
            "last_push": r.get("pushed_at"),
            "language": r.get("language"),
        }
    except Exception as e:
        return {"error": str(e), "repo": repo}


import asyncio  # noqa: E402  (needed for gather in get_repo_status)

ALL_TOOLS = [
    review_code,
    review_pr_diff,
    diagnose_leukemia,
    explain_diagnosis,
    clinical_reason,
    recall_patient,
    search_knowledge,
    query_knowledge_graph,
    create_github_issue,
    get_repo_status,
]
