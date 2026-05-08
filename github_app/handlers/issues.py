"""Handle issues webhook — route to meta-agent for autonomous resolution proposals."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from config import settings
from orchestrator.agent import run as agent_run

log = structlog.get_logger()

_http = httpx.AsyncClient(timeout=120.0)

AGENT_LABEL = "omnimed-nexus"
AUTO_RESOLVE_LABELS = {"bug", "enhancement", "code-quality"}

ISSUE_COMMENT_TEMPLATE = """\
## 🤖 OmniMed-Nexus Analysis

I've analysed this issue using the full OmniMed-Nexus system (codesense-ai + MedFusion-Leuk + medbrain-ai).

{analysis}

---
*Automated by [omnimed-nexus](https://github.com/{nexus_repo}). \
Human review required before any changes are applied.*
"""


async def handle_issue_event(payload: dict[str, Any], token: str) -> None:
    action = payload.get("action")
    if action not in ("opened", "labeled"):
        return

    issue = payload["issue"]
    repo_full = payload["repository"]["full_name"]
    labels = {lbl["name"] for lbl in issue.get("labels", [])}

    # Only auto-analyse if tagged with our label or a known auto-resolve label
    if AGENT_LABEL not in labels and not (labels & AUTO_RESOLVE_LABELS):
        return

    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue.get("body", "")

    log.info("issue_analysis_triggered", repo=repo_full, issue=issue_number)

    query = (
        f"GitHub Issue in {repo_full} — #{issue_number}: {issue_title}\n\n"
        f"Description:\n{issue_body[:2000]}\n\n"
        f"Analyse this issue. If it's a code problem, review the relevant code. "
        f"If it's a clinical/ML problem, use the appropriate diagnostic tools. "
        f"Propose a concrete resolution or next steps."
    )

    try:
        analysis = await agent_run(query=query, session_id=f"issue_{repo_full}_{issue_number}")
    except Exception as e:
        log.error("agent_run_failed", error=str(e))
        analysis = f"Agent analysis failed: {e}"

    comment_body = ISSUE_COMMENT_TEMPLATE.format(
        analysis=analysis,
        nexus_repo=settings.nexus_repo,
    )

    await _http.post(
        f"https://api.github.com/repos/{repo_full}/issues/{issue_number}/comments",
        json={"body": comment_body},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )

    log.info("issue_analysis_posted", repo=repo_full, issue=issue_number)
