"""Handle push webhook events — sync models and trigger downstream pipelines."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from config import settings
from orchestrator.memory import memory

log = structlog.get_logger()

_http = httpx.AsyncClient(timeout=60.0)

MODEL_FILE_EXTENSIONS = {".pt", ".pth", ".pkl", ".joblib", ".onnx", ".h5", ".keras", ".safetensors"}
CONFIG_FILES = {"requirements.txt", "pyproject.toml", "setup.py", "Dockerfile"}


async def handle_push_event(payload: dict[str, Any], token: str) -> None:
    repo_full = payload["repository"]["full_name"]
    ref = payload.get("ref", "")
    branch = ref.split("/")[-1]
    commits = payload.get("commits", [])

    if branch != payload["repository"].get("default_branch", "main"):
        return  # only process default branch pushes

    changed_files: set[str] = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    log.info("push_event", repo=repo_full, branch=branch, changed_files=len(changed_files))

    # Detect model file changes → trigger sync to medbrain-ai
    model_changes = [f for f in changed_files if any(f.endswith(ext) for ext in MODEL_FILE_EXTENSIONS)]
    if model_changes and repo_full == settings.medfusion_repo:
        await _sync_models_to_medbrain(model_changes, token)

    # Detect config changes → store in knowledge graph
    config_changes = [f for f in changed_files if any(c in f for c in CONFIG_FILES)]
    if config_changes:
        await memory.store_finding(
            repo=repo_full,
            finding_type="config_change",
            description=f"Config files changed: {', '.join(config_changes[:5])}",
            severity="low",
            metadata={"branch": branch, "files": list(config_changes)},
        )

    # Trigger cross-repo knowledge re-indexing for significant pushes
    if len(changed_files) > 5 or model_changes:
        await _dispatch_reindex(repo_full, token)


async def _sync_models_to_medbrain(model_files: list[str], token: str) -> None:
    """Notify medbrain-ai that MedFusion-Leuk has new model artifacts."""
    log.info("model_sync_triggered", files=model_files)
    try:
        resp = await _http.post(
            f"{settings.medbrain_api_url}/sync/models",
            json={
                "source_repo": settings.medfusion_repo,
                "model_files": model_files,
                "github_token": token,
            },
        )
        if resp.status_code == 200:
            log.info("model_sync_success")
        else:
            log.warning("model_sync_failed", status=resp.status_code)
    except httpx.HTTPError as e:
        log.error("model_sync_error", error=str(e))


async def _dispatch_reindex(repo: str, token: str) -> None:
    """Send a repository_dispatch to omnimed-nexus to trigger RAG re-indexing."""
    try:
        await _http.post(
            f"https://api.github.com/repos/{settings.nexus_repo}/dispatches",
            json={"event_type": "reindex", "client_payload": {"source_repo": repo}},
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        log.info("reindex_dispatch_sent", source_repo=repo)
    except httpx.HTTPError as e:
        log.error("reindex_dispatch_error", error=str(e))
