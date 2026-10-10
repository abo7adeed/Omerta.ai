"""LangGraph compilation and execution runner for Omerta.ai Agentic RAG.

Graph Architecture:
START -> validate_request -> understand_query_and_intent -> retrieve_selected_sources
      -> execute_validated_analysis -> generate_chart_if_required
      -> synthesize_structured_response -> validate_citations_and_results -> END
"""

import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from apps.agentic_rag import nodes
from apps.agentic_rag.state import AgenticRAGState
from domain.agentic_rag.schemas import (
    AgenticRAGRequest,
    AgenticRAGResponse,
    ResponseStatus,
)

logger = logging.getLogger(__name__)


def build_agentic_rag_graph() -> Any:
    """Build and compile the Agentic RAG StateGraph."""
    graph = StateGraph(AgenticRAGState)

    graph.add_node("validate_request", nodes.validate_request)
    graph.add_node("understand_query_and_intent", nodes.understand_query_and_intent)
    graph.add_node("retrieve_selected_sources", nodes.retrieve_selected_sources)
    graph.add_node("execute_validated_analysis", nodes.execute_validated_analysis)
    graph.add_node("generate_chart_if_required", nodes.generate_chart_if_required)
    graph.add_node("synthesize_structured_response", nodes.synthesize_structured_response)
    graph.add_node("validate_citations_and_results", nodes.validate_citations_and_results)

    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "understand_query_and_intent")
    graph.add_edge("understand_query_and_intent", "retrieve_selected_sources")
    graph.add_edge("retrieve_selected_sources", "execute_validated_analysis")
    graph.add_edge("execute_validated_analysis", "generate_chart_if_required")
    graph.add_edge("generate_chart_if_required", "synthesize_structured_response")
    graph.add_edge("synthesize_structured_response", "validate_citations_and_results")
    graph.add_edge("validate_citations_and_results", END)

    return graph.compile()


# Pre-compiled workflow instance
_COMPILED_GRAPH = None


def get_agentic_rag_graph() -> Any:
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_agentic_rag_graph()
    return _COMPILED_GRAPH


async def execute_agentic_rag(
    request: AgenticRAGRequest,
    user_role: str = "INVESTIGATOR",
    user_id: str | None = None,
) -> AgenticRAGResponse:
    """Execute the Agentic RAG pipeline asynchronously and return validated response."""
    t0 = time.perf_counter()
    graph = get_agentic_rag_graph()

    initial_state = AgenticRAGState(
        question=request.question,
        entity_ids=request.entity_ids,
        conversation_id=request.conversation_id,
        user_role=user_role,
        user_id=user_id,
    )

    final_dict = await graph.ainvoke(initial_state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Package into AgenticRAGResponse contract
    response = AgenticRAGResponse(
        status=final_dict.get("status", ResponseStatus.ANSWERED),
        answer=final_dict.get("answer", ""),
        citations=final_dict.get("citations", []),
        evidence_ids=final_dict.get("evidence_ids", []),
        sources_used=final_dict.get("sources_used", []),
        response_blocks=final_dict.get("response_blocks", []),
        limitations=final_dict.get("limitations", []),
        clarification_question=final_dict.get("clarification_question"),
        investigation_id=final_dict.get("investigation_id", f"rag-{uuid4().hex[:8]}"),
        execution_time_ms=round(elapsed_ms, 2),
        charts=final_dict.get("charts", []),
        thought_steps=final_dict.get("thought_steps", []),
        warnings=final_dict.get("warnings", []),
        conversation_id=request.conversation_id,
    )

    return response

