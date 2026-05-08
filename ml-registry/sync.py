"""Cross-repo model sync — when MedFusion-Leuk updates, notify medbrain-ai."""

from __future__ import annotations

import structlog

from config import settings
from ml_registry.registry import get_client, get_latest_model, list_all_models

log = structlog.get_logger()


async def sync_medfusion_to_medbrain() -> dict[str, str]:
    """Promote the latest MedFusion-Leuk model and notify medbrain-ai."""
    import httpx

    model_name = "MedFusion-Leuk-Ensemble"
    latest = get_latest_model(model_name, stage="Staging")

    if not latest:
        log.warning("no_staging_model", model=model_name)
        return {"status": "no_staging_model"}

    # Promote to Production
    client = get_client()
    client.transition_model_version_stage(
        name=model_name,
        version=latest["version"],
        stage="Production",
        archive_existing_versions=True,
    )
    log.info("model_promoted_to_production", model=model_name, version=latest["version"])

    # Notify medbrain-ai
    async with httpx.AsyncClient(timeout=30.0) as http:
        try:
            resp = await http.post(
                f"{settings.medbrain_api_url}/models/update",
                json={
                    "model_name": model_name,
                    "version": latest["version"],
                    "mlflow_run_id": latest["run_id"],
                    "tracking_uri": settings.mlflow_tracking_uri,
                },
            )
            resp.raise_for_status()
            log.info("medbrain_model_update_notified")
        except httpx.HTTPError as e:
            log.error("medbrain_notify_failed", error=str(e))

    return {
        "status": "synced",
        "model": model_name,
        "version": latest["version"],
    }


def registry_status() -> list[dict[str, object]]:
    """Return a summary of all registered models for the dashboard."""
    return list_all_models()
