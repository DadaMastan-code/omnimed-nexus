"""LLM-based query router — classifies incoming requests to target systems."""

from __future__ import annotations

import json
import re

import structlog
from anthropic import AsyncAnthropic

from config import settings
from orchestrator.prompts import ROUTER_PROMPT

log = structlog.get_logger()

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

VALID_TARGETS = {"codesense", "medfusion", "medbrain", "multi", "meta"}


async def route(query: str) -> dict[str, list[str] | str]:
    """Classify a query and return routing targets + reasoning.

    Returns: {"targets": [...], "reasoning": "..."}
    """
    prompt = ROUTER_PROMPT.format(query=query)

    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Extract JSON robustly
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        log.warning("router_parse_failed", raw=text)
        return {"targets": ["medbrain"], "reasoning": "fallback to medbrain"}

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        log.warning("router_json_invalid", raw=text)
        return {"targets": ["medbrain"], "reasoning": "fallback to medbrain"}

    # Sanitise targets
    targets = [t for t in result.get("targets", []) if t in VALID_TARGETS]
    if not targets:
        targets = ["medbrain"]

    # Expand "multi" into its constituent targets if it's the only one listed
    if targets == ["multi"]:
        targets = ["codesense", "medfusion", "medbrain"]

    log.info("router_decision", query=query[:80], targets=targets)
    return {"targets": targets, "reasoning": result.get("reasoning", "")}
