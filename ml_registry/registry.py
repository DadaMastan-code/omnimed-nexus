"""Unified MLflow model registry client spanning all three repos."""

from __future__ import annotations

from typing import Any

import mlflow
import mlflow.tracking
import structlog

from config import settings

log = structlog.get_logger()


def get_client() -> mlflow.tracking.MlflowClient:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return mlflow.tracking.MlflowClient()


def register_model(
    run_id: str,
    artifact_path: str,
    model_name: str,
    tags: dict[str, str] | None = None,
) -> str:
    """Register a model version and return its version number."""
    client = get_client()
    model_uri = f"runs:/{run_id}/{artifact_path}"
    mv = mlflow.register_model(model_uri=model_uri, name=model_name, tags=tags)
    log.info("model_registered", name=model_name, version=mv.version, run_id=run_id)
    return mv.version


def promote_model(model_name: str, version: str, stage: str = "Staging") -> None:
    """Promote a model version to Staging or Production."""
    client = get_client()
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=(stage == "Production"),
    )
    log.info("model_promoted", name=model_name, version=version, stage=stage)


def get_latest_model(model_name: str, stage: str = "Production") -> dict[str, Any] | None:
    """Return the latest model version metadata for a given stage."""
    client = get_client()
    versions = client.get_latest_versions(model_name, stages=[stage])
    if not versions:
        return None
    v = versions[0]
    return {
        "name": v.name,
        "version": v.version,
        "stage": v.current_stage,
        "run_id": v.run_id,
        "source": v.source,
        "creation_timestamp": v.creation_timestamp,
    }


def list_all_models() -> list[dict[str, Any]]:
    """List all registered models across the unified registry."""
    client = get_client()
    models = []
    for rm in client.search_registered_models():
        latest = {v.current_stage: v.version for v in rm.latest_versions}
        models.append({
            "name": rm.name,
            "tags": dict(rm.tags),
            "latest_versions": latest,
        })
    return models
