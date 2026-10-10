"""Typed state for the Agentic RAG LangGraph orchestrator."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from domain.agentic_rag.schemas import (
    AgenticRAGRouting,
    ChartArtifactReference,
    ChartSpecification,
    Citation,
    ComparisonResult,
    MetricResult,
    NormalizedEvidence,
    ResponseBlock,
    ResponseStatus,
    SourceType,
    StatisticalSummary,
    TableResult,
)
from pydantic import BaseModel, Field


class AgenticRAGState(BaseModel):
    """Execution state passed through the LangGraph nodes."""

    # Inbound parameters
    question: str
    entity_ids: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    user_role: str = "INVESTIGATOR"
    user_id: str | None = None

    # Routing and classification
    routing: AgenticRAGRouting = Field(default_factory=AgenticRAGRouting)

    # Retrieved multi-source evidence
    evidence: list[NormalizedEvidence] = Field(default_factory=list)

    # Deterministic analytical outputs
    metrics: list[MetricResult] = Field(default_factory=list)
    table: TableResult | None = None
    comparison: ComparisonResult | None = None
    stats: StatisticalSummary | None = None
    chart_spec: ChartSpecification | None = None
    chart_artifact: ChartArtifactReference | None = None
    charts: list[ChartArtifactReference] = Field(default_factory=list)

    # Conversational memory and guardrail tracking
    conversation_context: str = ""
    thought_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Final synthesis
    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    sources_used: list[SourceType] = Field(default_factory=list)
    response_blocks: list[ResponseBlock] = Field(default_factory=list)
    status: ResponseStatus = ResponseStatus.ANSWERED
    limitations: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    investigation_id: str = Field(default_factory=lambda: f"rag-inv-{uuid4().hex[:10]}")

    # Operational tracking
    errors: list[str] = Field(default_factory=list)
    node_timings_ms: dict[str, float] = Field(default_factory=dict)
    start_time: float = Field(default_factory=lambda: datetime.now(UTC).timestamp())

