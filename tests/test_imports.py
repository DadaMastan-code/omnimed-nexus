"""Smoke tests — verify all packages import cleanly."""


def test_orchestrator_imports() -> None:
    import orchestrator  # noqa: F401
    from orchestrator.prompts import META_AGENT_SYSTEM
    from orchestrator.router import VALID_TARGETS

    assert META_AGENT_SYSTEM
    assert "codesense" in VALID_TARGETS


def test_github_app_imports() -> None:
    from github_app.handlers.pr import PR_COMMENT_TEMPLATE
    from github_app.handlers.push import MODEL_FILE_EXTENSIONS

    assert ".pt" in MODEL_FILE_EXTENSIONS
    assert "OmniMed-Nexus" in PR_COMMENT_TEMPLATE


def test_rag_layer_imports() -> None:
    from rag_layer.embeddings import get_embedding_model  # noqa: F401
    from rag_layer.indexer import COLLECTION_NAME, VECTOR_SIZE

    assert COLLECTION_NAME == "omnimed_knowledge"
    assert VECTOR_SIZE == 384


def test_eval_harness_imports() -> None:
    from eval_harness.metrics import ClinicalMLMetrics, CodeQualityMetrics  # noqa: F401


def test_config_loads() -> None:
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
    from config import Settings
    s = Settings()
    assert "DadaMastan-code" in s.codesense_repo
