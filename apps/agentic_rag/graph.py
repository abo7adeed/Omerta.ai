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


def route_after_validate(state: AgenticRAGState) -> str:
    if state.status == ResponseStatus.INSUFFICIENT_EVIDENCE and state.errors:
        return "synthesize_structured_response"
    return "understand_query_and_intent"


def route_after_intent(state: AgenticRAGState) -> str:
    from domain.agentic_rag.schemas import AnalysisIntent
    intents = state.routing.analysis_intents
    if AnalysisIntent.OUT_OF_DOMAIN in intents or not state.routing.selected_sources:
        return "synthesize_structured_response"
    return "retrieve_selected_sources"


def route_after_retrieval(state: AgenticRAGState) -> str:
    if state.status == ResponseStatus.NEEDS_CLARIFICATION:
        return "synthesize_structured_response"
    from domain.agentic_rag.schemas import AnalysisIntent
    intents = state.routing.analysis_intents
    needs_analysis = any(i in intents for i in [
        AnalysisIntent.FINANCIAL_AGGREGATION,
        AnalysisIntent.AGGREGATION,
        AnalysisIntent.PERIOD_COMPARISON,
        AnalysisIntent.COMPARISON,
        AnalysisIntent.TREND_ANALYSIS,
        AnalysisIntent.VISUALIZATION,
        AnalysisIntent.TRANSACTION_LOOKUP,
    ]) or state.routing.chart_requested
    if needs_analysis:
        return "execute_validated_analysis"
    return "synthesize_structured_response"


def route_after_analysis(state: AgenticRAGState) -> str:
    from domain.agentic_rag.schemas import AnalysisIntent
    if state.routing.chart_requested or AnalysisIntent.VISUALIZATION in state.routing.analysis_intents:
        return "generate_chart_if_required"
    return "synthesize_structured_response"


def build_agentic_rag_graph() -> Any:
    """Build and compile the Agentic RAG StateGraph with conditional execution."""
    graph = StateGraph(AgenticRAGState)

    graph.add_node("validate_request", nodes.validate_request)
    graph.add_node("understand_query_and_intent", nodes.understand_query_and_intent)
    graph.add_node("retrieve_selected_sources", nodes.retrieve_selected_sources)
    graph.add_node("execute_validated_analysis", nodes.execute_validated_analysis)
    graph.add_node("generate_chart_if_required", nodes.generate_chart_if_required)
    graph.add_node("synthesize_structured_response", nodes.synthesize_structured_response)
    graph.add_node("validate_citations_and_results", nodes.validate_citations_and_results)

    graph.add_edge(START, "validate_request")
    graph.add_conditional_edges("validate_request", route_after_validate, {
        "synthesize_structured_response": "synthesize_structured_response",
        "understand_query_and_intent": "understand_query_and_intent",
    })
    graph.add_conditional_edges("understand_query_and_intent", route_after_intent, {
        "synthesize_structured_response": "synthesize_structured_response",
        "retrieve_selected_sources": "retrieve_selected_sources",
    })
    graph.add_conditional_edges("retrieve_selected_sources", route_after_retrieval, {
        "execute_validated_analysis": "execute_validated_analysis",
        "synthesize_structured_response": "synthesize_structured_response",
    })
    graph.add_conditional_edges("execute_validated_analysis", route_after_analysis, {
        "generate_chart_if_required": "generate_chart_if_required",
        "synthesize_structured_response": "synthesize_structured_response",
    })
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

    from infrastructure.observability import get_langfuse_callback

    cb = get_langfuse_callback(
        session_id=request.conversation_id,
        user_id=user_id,
        tags=["agentic_rag"],
        metadata={"question": request.question, "user_role": user_role},
    )
    config = {"callbacks": [cb]} if cb else None

    final_dict = await graph.ainvoke(initial_state, config=config)
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
        forensic_trace=final_dict.get("forensic_trace", []),
        conversation_id=request.conversation_id,
    )

    return response

