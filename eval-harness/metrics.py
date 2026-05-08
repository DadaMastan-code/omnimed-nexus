"""Metric definitions for code quality and clinical ML evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class CodeQualityMetrics:
    security_score: float       # 0-10
    performance_score: float    # 0-10
    architecture_score: float   # 0-10
    test_coverage: float        # 0-10
    docs_score: float           # 0-10
    issue_count: int
    critical_issues: int

    @property
    def overall(self) -> float:
        return np.mean([
            self.security_score,
            self.performance_score,
            self.architecture_score,
            self.test_coverage,
            self.docs_score,
        ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "security": self.security_score,
            "performance": self.performance_score,
            "architecture": self.architecture_score,
            "test_coverage": self.test_coverage,
            "docs": self.docs_score,
            "overall": round(self.overall, 2),
            "issues": self.issue_count,
            "critical_issues": self.critical_issues,
        }


@dataclass
class ClinicalMLMetrics:
    y_true: list[int]
    y_pred: list[int]
    y_prob: list[float] | None = None

    @property
    def accuracy(self) -> float:
        return round(accuracy_score(self.y_true, self.y_pred), 4)

    @property
    def precision(self) -> float:
        return round(precision_score(self.y_true, self.y_pred, average="macro", zero_division=0), 4)

    @property
    def recall(self) -> float:
        return round(recall_score(self.y_true, self.y_pred, average="macro", zero_division=0), 4)

    @property
    def f1(self) -> float:
        return round(f1_score(self.y_true, self.y_pred, average="macro", zero_division=0), 4)

    @property
    def auc(self) -> float | None:
        if self.y_prob is None:
            return None
        try:
            return round(roc_auc_score(self.y_true, self.y_prob, multi_class="ovr"), 4)
        except Exception:
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_macro": self.f1,
            "auc_ovr": self.auc,
        }
