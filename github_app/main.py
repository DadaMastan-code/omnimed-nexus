"""GitHub App webhook server — receives events from all three monitored repos."""

from __future__ import annotations

import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from github_app.auth import get_installation_token
from github_app.handlers.issues import handle_issue_event
from github_app.handlers.pr import handle_pr_event
from github_app.handlers.push import handle_push_event
from orchestrator.memory import memory

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await memory.connect()
    log.info("neo4j_connected")
    yield
    await memory.close()
    log.info("neo4j_disconnected")


app = FastAPI(
    title="OmniMed-Nexus GitHub App",
    description="Webhook receiver and orchestrator hub for codesense-ai, MedFusion-Leuk, medbrain-ai",
    version="0.1.0",
    lifespan=lifespan,
)


def _verify_signature(body: bytes, signature: str) -> bool:
    if not settings.github_webhook_secret:
        return True  # Skip in dev; enforce in prod
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(""),
) -> JSONResponse:
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    repo_full = payload.get("repository", {}).get("full_name", "")
    if repo_full not in settings.all_repos and repo_full != settings.nexus_repo:
        log.debug("webhook_ignored", repo=repo_full, event=x_github_event)
        return JSONResponse({"status": "ignored"})

    installation_id = payload.get("installation", {}).get("id")
    if not installation_id and not settings.github_token:
        raise HTTPException(status_code=400, detail="No installation ID or token")

    async def _get_token() -> str:
        if installation_id:
            return await get_installation_token(installation_id)
        return settings.github_token

    log.info("webhook_received", event=x_github_event, repo=repo_full)

    if x_github_event == "pull_request":
        token = await _get_token()
        background_tasks.add_task(handle_pr_event, payload, token)

    elif x_github_event == "push":
        token = await _get_token()
        background_tasks.add_task(handle_push_event, payload, token)

    elif x_github_event == "issues":
        token = await _get_token()
        background_tasks.add_task(handle_issue_event, payload, token)

    elif x_github_event == "repository_dispatch":
        event_type = payload.get("action")
        log.info("repo_dispatch", event_type=event_type)
        if event_type == "reindex":
            from rag_layer.indexer import index_repo
            source_repo = payload.get("client_payload", {}).get("source_repo", "")
            background_tasks.add_task(index_repo, source_repo)

    return JSONResponse({"status": "accepted"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "omnimed-nexus-github-app"}


@app.get("/findings")
async def list_findings(repo: str | None = None) -> list[dict[str, Any]]:
    """List open findings tracked in Neo4j."""
    return await memory.get_open_findings(repo=repo)


@app.post("/query")
async def query_agent(body: dict[str, str]) -> dict[str, str]:
    """Direct query endpoint for the meta-agent."""
    from orchestrator.agent import run as agent_run
    answer = await agent_run(
        query=body.get("query", ""),
        session_id=body.get("session_id", "api"),
    )
    return {"answer": answer}
