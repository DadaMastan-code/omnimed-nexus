"""Unified evaluator — runs benchmarks across code quality and clinical ML."""

from __future__ import annotations

from typing import Any

import mlflow
import structlog

from config import settings
from eval_harness.metrics import ClinicalMLMetrics, CodeQualityMetrics

log = structlog.get_logger()


class NexusEvaluator:
    """Orchestrates evaluation across all three repos and logs to MLflow."""

    def __init__(self) -> None:
        self._initialized = False

    def _ensure_mlflow(self) -> None:
        if not self._initialized:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_experiment_name)
            self._initialized = True

    async def evaluate_code_quality(self, repo: str, codesense_review: dict[str, Any]) -> CodeQualityMetrics:
        """Parse a codesense-ai review into structured metrics."""
        self._ensure_mlflow()
        scores = codesense_review.get("scores", {})
        issues = codesense_review.get("issues", [])

        metrics = CodeQualityMetrics(
            security_score=scores.get("security", 0.0),
            performance_score=scores.get("performance", 0.0),
            architecture_score=scores.get("architecture", 0.0),
            test_coverage=scores.get("tests", 0.0),
            docs_score=scores.get("docs", 0.0),
            issue_count=len(issues),
            critical_issues=sum(1 for i in issues if i.get("severity") == "critical"),
        )

        with mlflow.start_run(run_name=f"code_quality_{repo.replace('/', '_')}"):
            mlflow.log_param("repo", repo)
            mlflow.log_metrics(metrics.to_dict())

        log.info("code_quality_evaluated", repo=repo, overall=metrics.overall)
        return metrics

    async def evaluate_clinical_model(
        self,
        model_name: str,
        y_true: list[int],
        y_pred: list[int],
        y_prob: list[float] | None = None,
        tags: dict[str, str] | None = None,
    ) -> ClinicalMLMetrics:
        """Evaluate a clinical ML model and log metrics to MLflow."""
        self._ensure_mlflow()
        metrics = ClinicalMLMetrics(y_true=y_true, y_pred=y_pred, y_prob=y_prob)
        result = metrics.to_dict()

        with mlflow.start_run(run_name=f"eval_{model_name}"):
            mlflow.log_param("model_name", model_name)
            mlflow.log_params(tags or {})
            mlflow.log_metrics({k: v for k, v in result.items() if v is not None})

        log.info("clinical_model_evaluated", model=model_name, **result)
        return metrics

    async def run_full_evaluation(self) -> dict[str, Any]:
        """Run evaluation across all systems and return a summary report."""
        import httpx

        report: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=60.0) as http:
            # codesense-ai health
            try:
                r = await http.get(f"{settings.codesense_api_url}/health")
                report["codesense_status"] = "up" if r.status_code == 200 else "degraded"
            except Exception:
                report["codesense_status"] = "down"

            # MedFusion-Leuk health
            try:
                r = await http.get(f"{settings.medfusion_api_url}/health")
                report["medfusion_status"] = "up" if r.status_code == 200 else "degraded"
            except Exception:
                report["medfusion_status"] = "down"

            # medbrain-ai health
            try:
                r = await http.get(f"{settings.medbrain_api_url}/health")
                report["medbrain_status"] = "up" if r.status_code == 200 else "degraded"
            except Exception:
                report["medbrain_status"] = "down"

        log.info("full_evaluation_complete", **report)
        return report


evaluator = NexusEvaluator()
