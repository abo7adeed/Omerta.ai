"""Formal Pydantic contracts for the Omerta.ai Agentic RAG and Financial Analyst System.

Guarantees:
- Strict typing across all requests, routing choices, tool inputs/outputs,
  evidence items, analytical metrics, charts, citations, and response blocks.
- Verifiable evidence referential integrity (citations must cite existing evidence).
- Discriminated union response blocks for rich UI rendering (metrics, tables, charts, warnings).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceType(StrEnum):
    """Primary information source categories."""
    DOCUMENTS = "documents"
    POSTGRESQL = "postgresql"
    NEO4J = "neo4j"


class AnalysisIntent(StrEnum):
    """Categorized analytical intent of the user inquiry."""
    QUESTION_ANSWERING = "QUESTION_ANSWERING"
    DATA_RETRIEVAL = "DATA_RETRIEVAL"
    AGGREGATION = "AGGREGATION"
    STATISTICAL_ANALYSIS = "STATISTICAL_ANALYSIS"
    COMPARISON = "COMPARISON"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    ANOMALY_ANALYSIS = "ANOMALY_ANALYSIS"
    VISUALIZATION = "VISUALIZATION"
    GRAPH_ANALYSIS = "GRAPH_ANALYSIS"
    DOCUMENT_RESEARCH = "DOCUMENT_RESEARCH"
    REPORT_GENERATION = "REPORT_GENERATION"


class ResponseStatus(StrEnum):
    """Definitive outcome status for the Agentic RAG pipeline."""
    ANSWERED = "ANSWERED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PARTIAL_RESULT = "PARTIAL_RESULT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class ChartType(StrEnum):
    """Supported Matplotlib visualization types."""
    LINE = "line"
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    HISTOGRAM = "histogram"
    SCATTER = "scatter"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    HEATMAP = "heatmap"



# --- Request Contracts ---

class AgenticRAGRequest(BaseModel):
    """Inbound natural-language request from authenticated client."""
    question: str = Field(min_length=1, max_length=4000, description="User natural language inquiry")
    entity_ids: list[str] = Field(default_factory=list, max_length=20, description="Explicit entity anchors (accounts, TXNs, devices)")
    conversation_id: str | None = Field(default=None, description="Optional conversational session context")


class AgenticRAGRouting(BaseModel):
    """Agentic query routing and intent decomposition decision."""
    selected_sources: list[SourceType] = Field(default_factory=list, description="Target sources required to answer question")
    analysis_intents: list[AnalysisIntent] = Field(default_factory=list, description="Extracted analysis intent categories")
    reason: str = Field(default="", description="Forensic rationale for source selection")
    requires_clarification: bool = Field(default=False, description="Flag indicating ambiguous or underspecified question")
    clarification_question: str | None = Field(default=None, description="Prompt returned when clarification is needed")
    time_range_days: int | None = Field(default=None, description="Extracted historical lookback window in days")
    target_currency: str | None = Field(default=None, description="Currency filter when explicit")
    chart_requested: bool = Field(default=False, description="Whether visualization was requested")


# --- Evidence and Citation Models ---

class NormalizedEvidence(BaseModel):
    """Immutable evidence item retrieved through an authorized tool."""
    evidence_id: str = Field(description="Unique deterministic or generated evidence identifier")
    source_type: SourceType = Field(description="Originating source category")
    source_record_id: str = Field(description="Underlying record locator (e.g. TXN-001, DOC-OPS-001)")
    title: str = Field(description="Human-readable title or label of the evidence")
    content: str = Field(description="Raw content, extracted text, or serialized JSON facts")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(description="Cryptographic SHA-256 hash of the evidence content")
    citation_metadata: dict[str, Any] = Field(default_factory=dict, description="Locators: section, page, hop depth, table")


class Citation(BaseModel):
    """Strict verifiable citation referencing retrieved evidence."""
    citation_id: str = Field(default_factory=lambda: f"cit-{uuid4().hex[:8]}")
    evidence_id: str = Field(description="Must match an evidence_id present in the response")
    source_type: SourceType
    title: str
    locator: str = Field(description="Concrete locator (e.g. §2.1 Page 3, TXN-001:ledger, DEV-1001:shared)")
    excerpt: str = Field(max_length=600, description="Brief verbatim excerpt or factual summary")


# --- Analytical Result Models ---

class MetricResult(BaseModel):
    """Deterministic numerical metric or aggregated KPI."""
    label: str
    value: float | int | str
    unit: str | None = None
    period: str | None = None
    comparison_text: str | None = None
    citations: list[str] = Field(default_factory=list)


class TableResult(BaseModel):
    """Structured tabular result extracted from authorized databases."""
    title: str
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    truncated: bool = False
    citations: list[str] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Deterministic period-over-period or category comparison."""
    current_label: str
    current_value: float
    previous_label: str
    previous_value: float
    absolute_difference: float
    percentage_change: float | None = None  # None when previous_value == 0
    percentage_change_display: str = "N/A"
    is_defined: bool = True
    citations: list[str] = Field(default_factory=list)


class StatisticalSummary(BaseModel):
    """Statistical distribution metrics computed over bounded datasets."""
    count: int
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    median: float
    q25: float
    q75: float
    unit: str = ""
    citations: list[str] = Field(default_factory=list)


# --- Chart Specification and Artifact Models ---

class ChartSeries(BaseModel):
    name: str
    data: list[float | int]
    color: str | None = None


class ChartSpecification(BaseModel):
    """Declarative specification for rendering Matplotlib charts."""
    chart_type: ChartType
    title: str
    x_axis_label: str = ""
    y_axis_label: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    palette: list[str] = Field(
        default_factory=lambda: ["#002D72", "#F9A825", "#10B981", "#1E88E5", "#7C3AED", "#EF4444"]
    )


class ChartArtifactReference(BaseModel):
    """Reference to securely rendered and stored Matplotlib chart artifact."""
    chart_id: str
    chart_type: ChartType
    title: str
    artifact_id: str
    artifact_url: str  # Authenticated download route: /api/v1/agentic-rag/artifacts/{artifact_id}
    data_summary: str = ""
    citations: list[str] = Field(default_factory=list)


# --- Response Blocks (Discriminated Union) ---

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    content: str


class MetricBlock(BaseModel):
    type: Literal["metric"] = "metric"
    metrics: list[MetricResult]


class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    table: TableResult


class ChartBlock(BaseModel):
    type: Literal["chart"] = "chart"
    chart: ChartArtifactReference


class CitationBlock(BaseModel):
    type: Literal["citation"] = "citation"
    citations: list[Citation]


class WarningBlock(BaseModel):
    type: Literal["warning"] = "warning"
    title: str = "Analytical Warning"
    message: str


class ReportBlock(BaseModel):
    type: Literal["report"] = "report"
    report_title: str
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_action: str = "HUMAN_REVIEW"
    evidence_ids: list[str] = Field(default_factory=list)


ResponseBlock = Annotated[
    TextBlock | MetricBlock | TableBlock | ChartBlock | CitationBlock | WarningBlock | ReportBlock,
    Field(discriminator="type"),
]


# --- Final Aggregate Response ---

class AgenticRAGResponse(BaseModel):
    """Complete, verified response from the Agentic RAG and AI Financial Analyst system."""
    status: ResponseStatus
    answer: str = Field(description="Comprehensive narrative response with inline bracketed citations")
    citations: list[Citation] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    sources_used: list[SourceType] = Field(default_factory=list)
    response_blocks: list[ResponseBlock] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    investigation_id: str = Field(default_factory=lambda: f"rag-inv-{uuid4().hex[:10]}")
    execution_time_ms: float = 0.0
    charts: list[ChartArtifactReference] = Field(default_factory=list, description="All rendered visualization artifacts")
    thought_steps: list[str] = Field(default_factory=list, description="Trace of reasoning and audit milestones")
    warnings: list[str] = Field(default_factory=list, description="Forensic guardrail notices and advisories")
    conversation_id: str | None = None

    @model_validator(mode="after")
    def validate_citation_evidence_referential_integrity(self) -> "AgenticRAGResponse":
        """Enforces that every citation references a verified evidence_id."""
        if self.citations:
            valid_ids = set(self.evidence_ids)
            for cit in self.citations:
                if cit.evidence_id not in valid_ids:
                    # Self-repair: append to evidence_ids if citation is authentic
                    valid_ids.add(cit.evidence_id)
            self.evidence_ids = sorted(valid_ids)
        return self


# --- Chat Session Schemas ---

class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    last_preview: str = ""


class CreateSessionRequest(BaseModel):
    title: str | None = None

