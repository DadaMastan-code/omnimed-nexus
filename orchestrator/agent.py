"""OmniMed-Nexus Meta-Agent — LangGraph orchestrator commanding all three systems."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import structlog
from anthropic import AsyncAnthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import settings
from orchestrator.memory import memory
from orchestrator.prompts import META_AGENT_SYSTEM, SYNTHESIZER_PROMPT
from orchestrator.router import route
from orchestrator.tools import (
    ALL_TOOLS,
)

log = structlog.get_logger()


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    session_id: str
    routing_targets: list[str]
    routing_reasoning: str
    tool_results: dict[str, Any]
    final_answer: str
    error: str | None


# ── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=settings.anthropic_api_key,
    max_tokens=4096,
).bind_tools(ALL_TOOLS)


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def router_node(state: AgentState) -> dict[str, Any]:
    """Classify the query and set routing targets."""
    routing = await route(state["query"])
    return {
        "routing_targets": routing["targets"],
        "routing_reasoning": routing["reasoning"],
        "messages": [
            SystemMessage(content=META_AGENT_SYSTEM),
            HumanMessage(content=state["query"]),
        ],
    }


async def agent_node(state: AgentState) -> dict[str, Any]:
    """Main LLM call — may invoke tools based on routing targets."""
    context_hint = (
        f"\n\n[Router] Suggested targets: {state['routing_targets']}. "
        f"Reasoning: {state['routing_reasoning']}\n"
        f"Invoke the appropriate tools now."
    )

    messages = list(state["messages"])
    if messages and isinstance(messages[-1], HumanMessage):
        messages[-1] = HumanMessage(content=messages[-1].content + context_hint)

    response = await llm.ainvoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """Route to tools or to synthesizer."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "synthesize"


async def synthesize_node(state: AgentState) -> dict[str, Any]:
    """Collect all tool results and produce final synthesized answer."""
    tool_msgs = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    results_text = "\n\n".join(
        f"**{m.name}**:\n{m.content}" for m in tool_msgs
    )

    prompt = SYNTHESIZER_PROMPT.format(query=state["query"], results=results_text or "No tool results.")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text

    # Persist interaction to Neo4j memory
    try:
        await memory.store_interaction(
            session_id=state["session_id"],
            query=state["query"],
            targets=state["routing_targets"],
            response_summary=answer[:500],
        )
    except Exception as e:
        log.warning("memory_store_failed", error=str(e))

    return {"final_answer": answer}


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph() -> Any:
    tool_node = ToolNode(ALL_TOOLS)

    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tool_node)
    g.add_node("synthesize", synthesize_node)

    g.set_entry_point("router")
    g.add_edge("router", "agent")
    g.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "synthesize": "synthesize"},
    )
    g.add_edge("tools", "agent")   # loop back so agent can chain tools
    g.add_edge("synthesize", END)

    return g.compile()


graph = build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

async def run(query: str, session_id: str = "default") -> str:
    """Execute a query through the meta-agent and return the final answer."""
    initial_state: AgentState = {
        "messages": [],
        "query": query,
        "session_id": session_id,
        "routing_targets": [],
        "routing_reasoning": "",
        "tool_results": {},
        "final_answer": "",
        "error": None,
    }

    log.info("agent_run_start", query=query[:80], session_id=session_id)
    result = await graph.ainvoke(initial_state)
    log.info("agent_run_complete", session_id=session_id)
    return result["final_answer"]
