"""Comprehensive unit and integration test suite for Omerta.ai LLM-as-a-Judge Evaluation.

Covers:
- Valid and invalid judge responses and score range constraints.
- Deterministic checks (fabricated identifiers, amount mismatches, graph topology, citations).
- Retry limits, malformed response recovery, and provider failure handling.
- Disabled evaluation mode.
- Langfuse score association and trace recording with mocks (zero live API keys required).
- Benchmark dataset scenario coverage and runner verification.
"""

from decimal import Decimal
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from domain.evaluation.benchmark import BenchmarkRunner, get_benchmark_scenarios
from domain.evaluation.deterministic import DeterministicValidator
from domain.evaluation.evaluator import InvestigationEvaluator
from domain.evaluation.judge_provider import FakeJudgeLLMProvider
from domain.evaluation.langfuse_reporter import record_evaluation_to_langfuse
from domain.evaluation.schemas import (
    DeterministicCheckItem,
    DeterministicValidationResult,
    EvaluationScores,
    EvaluationStatus,
    InvestigationEvaluationResult,
    JudgeRawOutput,
)
from infrastructure.config import get_settings
from infrastructure.llm.base import LLMResponse


# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _setup_eval_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    settings = get_settings()
    monkeypatch.setattr(settings, "use_local_llm", False, raising=False)
    monkeypatch.setattr(settings, "omerta_evaluation_provider", "fake", raising=False)
    monkeypatch.setattr(settings, "langfuse_enabled", False, raising=False)


# 1. Score Range & Schema Validation Tests
# --------------------------------------------------------------------------- #


def test_evaluation_scores_valid_ranges() -> None:
    """Scores between 1 and 5 (or None) are accepted."""
    scores = EvaluationScores(
        evidence_grounding=5,
        reasoning_quality=4,
        investigation_completeness=3,
        report_quality=2,
        overall_quality=1,
    )
    assert scores.evidence_grounding == 5
    assert scores.overall_quality == 1

    # Null / None is explicitly allowed for dimensions that cannot be evaluated
    partial = EvaluationScores(
        evidence_grounding=4,
        reasoning_quality=None,
        investigation_completeness=None,
        report_quality=5,
        overall_quality=4,
    )
    assert partial.reasoning_quality is None
    assert partial.report_quality == 5


def test_evaluation_scores_rejects_out_of_bounds() -> None:
    """Scores below 1 or above 5 must raise a ValidationError."""
    with pytest.raises(ValidationError):
        EvaluationScores(evidence_grounding=0)

    with pytest.raises(ValidationError):
        EvaluationScores(overall_quality=6)

    with pytest.raises(ValidationError):
        EvaluationScores(reasoning_quality=-1)


def test_human_review_policy_enforcement() -> None:
    """Deterministic policy guardrail forces human_review_required=True on severe flaws."""
    # Low overall score triggers human review
    result = InvestigationEvaluationResult(
        investigation_id="INV-TEST-01",
        scores=EvaluationScores(
            evidence_grounding=4,
            reasoning_quality=4,
            investigation_completeness=4,
            report_quality=4,
            overall_quality=2,
        ),
        human_review_required=False,
    )
    assert result.human_review_required is True
    assert any("Critically low overall" in r for r in result.review_reasons)

    # Deterministic failure triggers human review
    det = DeterministicValidationResult(
        passed=False,
        discrepancies=["Fabricated transaction ID: TXN-FAKE-123"],
    )
    result2 = InvestigationEvaluationResult(
        investigation_id="INV-TEST-02",
        scores=EvaluationScores(
            evidence_grounding=5,
            reasoning_quality=5,
            investigation_completeness=5,
            report_quality=5,
            overall_quality=5,
        ),
        deterministic_validation=det,
        human_review_required=False,
    )
    assert result2.human_review_required is True
    assert any("TXN-FAKE-123" in r for r in result2.review_reasons)


# --------------------------------------------------------------------------- #
# 2. Deterministic Validation Unit Tests
# --------------------------------------------------------------------------- #


def test_deterministic_validator_clean_report() -> None:
    """A clean, well-grounded report passes with zero discrepancies."""
    validator = DeterministicValidator()
    report = {
        "investigation_id": "INV-001",
        "transaction_id": "TXN-001",
        "risk_level": "HIGH",
        "summary": "Transfer of $8,400.00 from ACC-1001 to ACC-2002 via wire.",
        "findings": [
            {
                "finding": "Transfer of $8,400.00 initiated from new IP.",
                "evidence_ids": ["EV-01"],
            }
        ],
        "recommended_action": "HUMAN_REVIEW",
    }
    evidence = [
        {
            "evidence_id": "EV-01",
            "category": "TRANSACTION",
            "reference": "TXN-001",
            "description": "Wire transfer $8,400.00",
            "data": {"amount": "8400.00", "currency": "USD"},
        }
    ]
    context = {
        "transaction_id": "TXN-001",
        "amount": "8400.00",
        "transaction": {"amount": "8400.00", "sender": {"external_id": "ACC-1001"}},
    }

    result = validator.validate(report, evidence, context)
    assert result.passed is True
    assert len(result.discrepancies) == 0
    assert result.amounts_valid is True
    assert result.transaction_ids_valid is True


def test_deterministic_validator_detects_fabricated_transaction_id() -> None:
    """Detects transaction IDs in report that do not exist in evidence/context."""
    validator = DeterministicValidator()
    report = {
        "investigation_id": "INV-002",
        "transaction_id": "TXN-REAL-1",
        "risk_level": "HIGH",
        "summary": "Subject conducted structured transfer TXN-REAL-1 and fabricated transfer TXN-99999-FAKE.",
        "findings": [{"finding": "Hallucinated link", "evidence_ids": ["EV-01"]}],
        "recommended_action": "ESCALATE_TO_FIU",
    }
    evidence = [
        {"evidence_id": "EV-01", "category": "TRANSACTION", "reference": "TXN-REAL-1"}
    ]
    context = {"transaction_id": "TXN-REAL-1"}

    result = validator.validate(report, evidence, context)
    assert result.passed is False
    assert result.transaction_ids_valid is False
    assert any("TXN-99999-FAKE" in d for d in result.discrepancies)


def test_deterministic_validator_detects_incorrect_amount() -> None:
    """Detects conflicting financial amounts stated in report vs verified evidence."""
    validator = DeterministicValidator()
    report = {
        "investigation_id": "INV-003",
        "transaction_id": "TXN-003",
        "risk_level": "HIGH",
        "summary": "Urgent alert: transfer of $85,000.00 was executed.",
        "findings": [{"finding": "Massive wire of $85,000.00.", "evidence_ids": ["EV-01"]}],
        "recommended_action": "ESCALATE_TO_FIU",
    }
    evidence = [
        {
            "evidence_id": "EV-01",
            "category": "TRANSACTION",
            "reference": "TXN-003",
            "data": {"amount": "8500.00"},
        }
    ]
    context = {"transaction_id": "TXN-003", "transaction": {"amount": "8500.00"}}

    result = validator.validate(report, evidence, context)
    assert result.passed is False
    assert result.amounts_valid is False
    assert any("85,000" in d and "8500" in d for d in result.discrepancies)


def test_deterministic_validator_detects_missing_evidence_citation() -> None:
    """Detects findings that cite nonexistent evidence IDs."""
    validator = DeterministicValidator()
    report = {
        "investigation_id": "INV-004",
        "transaction_id": "TXN-004",
        "risk_level": "MEDIUM",
        "summary": "Transfer analysis.",
        "findings": [
            {
                "finding": "Suspicious login from unexpected device.",
                "evidence_ids": ["EV-DOES-NOT-EXIST"],
            }
        ],
        "recommended_action": "MONITOR",
    }
    evidence = [{"evidence_id": "EV-001", "reference": "TXN-004"}]
    context = {"transaction_id": "TXN-004"}

    result = validator.validate(report, evidence, context)
    assert result.passed is False
    assert result.evidence_references_valid is False
    assert any("EV-DOES-NOT-EXIST" in d for d in result.discrepancies)


def test_deterministic_validator_detects_unsupported_graph_relationship() -> None:
    """Detects assertions of corporate parent/subsidiary relationship without graph proof."""
    validator = DeterministicValidator()
    report = {
        "investigation_id": "INV-005",
        "transaction_id": "TXN-005",
        "risk_level": "LOW",
        "summary": "Transfer is routine because Account B is a wholly owned subsidiary of Account A.",
        "findings": [{"finding": "Subsidiary relationship confirmed.", "evidence_ids": ["EV-01"]}],
        "recommended_action": "CLOSE_NO_ACTION",
    }
    evidence = [{"evidence_id": "EV-01", "category": "TRANSACTION", "reference": "TXN-005"}]
    context = {"transaction_id": "TXN-005"}

    result = validator.validate(report, evidence, context)
    assert result.passed is False
    assert result.relationships_valid is False
    assert any("subsidiary" in d.lower() for d in result.discrepancies)


# --------------------------------------------------------------------------- #
# 3. Evaluator Engine & Retry / Failure Handling Tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_evaluator_disabled_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """When OMERTA_EVALUATION_ENABLED=False and force_run=False, returns SKIPPED."""
    settings = get_settings()
    monkeypatch.setattr(settings, "omerta_evaluation_enabled", False, raising=False)

    evaluator = InvestigationEvaluator()
    result = await evaluator.evaluate(
        investigation_id="INV-DIS-1",
        report={"summary": "Sample report", "recommended_action": "MONITOR", "findings": []},
        evidence=[],
        force_run=False,
    )
    assert result.status == EvaluationStatus.SKIPPED
    assert "skipped" in result.summary.lower()


@pytest.mark.asyncio
async def test_evaluator_successful_run_with_fake_judge() -> None:
    """Evaluates an investigation cleanly using the deterministic fake judge provider."""
    evaluator = InvestigationEvaluator(judge_provider=FakeJudgeLLMProvider())
    report = {
        "investigation_id": "INV-CLEAN-1",
        "transaction_id": "TXN-CLEAN-1",
        "risk_level": "LOW",
        "summary": "Transfer was verified against historical payroll.",
        "findings": [{"finding": "Payroll match", "evidence_ids": ["EV-01"]}],
        "recommended_action": "CLOSE_NO_ACTION",
    }
    evidence = [{"evidence_id": "EV-01", "reference": "TXN-CLEAN-1"}]
    context = {"transaction_id": "TXN-CLEAN-1"}

    result = await evaluator.evaluate(
        investigation_id="INV-CLEAN-1",
        report=report,
        evidence=evidence,
        context=context,
        force_run=True,
    )
    assert result.status == EvaluationStatus.COMPLETED
    assert result.scores.overall_quality == 5
    assert result.scores.evidence_grounding == 5
    assert result.human_review_required is False


@pytest.mark.asyncio
async def test_evaluator_recovers_from_malformed_json_on_retry() -> None:
    """When judge initially outputs malformed markdown or invalid JSON, it retries and succeeds."""
    mock_provider = MagicMock()
    mock_provider.name = "mock-flaky-judge"
    mock_provider.model = "mock-model"

    valid_judge_dict = {
        "scores": {
            "evidence_grounding": 4,
            "reasoning_quality": 4,
            "investigation_completeness": 4,
            "report_quality": 4,
            "overall_quality": 4,
        },
        "dimension_explanations": {},
        "unsupported_claims": [],
        "evidence_gaps": [],
        "strengths": ["Clear citations"],
        "weaknesses": [],
        "human_review_required": False,
        "review_reasons": [],
        "summary": "Recovered successfully on retry.",
    }

    # First call returns broken JSON; second call returns valid JSON inside code fences
    mock_provider.complete = AsyncMock(
        side_effect=[
            LLMResponse(content="Sorry, here is the answer: {not valid json}", provider="mock", model="m"),
            LLMResponse(content=f"```json\n{json.dumps(valid_judge_dict)}\n```", provider="mock", model="m"),
        ]
    )

    evaluator = InvestigationEvaluator(judge_provider=mock_provider)
    result = await evaluator.evaluate(
        investigation_id="INV-RETRY-1",
        report={"summary": "Sample report", "recommended_action": "MONITOR", "findings": [{"finding": "F1", "evidence_ids": ["EV-01"]}]},
        evidence=[{"evidence_id": "EV-01", "reference": "TXN-01"}],
        context={"transaction_id": "TXN-01"},
        force_run=True,
    )
    assert result.status == EvaluationStatus.COMPLETED
    assert result.scores.overall_quality == 4
    assert mock_provider.complete.call_count == 2


@pytest.mark.asyncio
async def test_evaluator_exhausts_retries_and_marks_failed() -> None:
    """When judge continuously fails or returns invalid schema, marks status=FAILED safely."""
    mock_provider = MagicMock()
    mock_provider.name = "mock-broken-judge"
    mock_provider.model = "mock-model"
    mock_provider.complete = AsyncMock(
        return_value=LLMResponse(content="Complete gibberish that cannot parse.", provider="mock", model="m")
    )

    evaluator = InvestigationEvaluator(judge_provider=mock_provider)
    result = await evaluator.evaluate(
        investigation_id="INV-FAIL-1",
        report={"summary": "Sample report", "recommended_action": "MONITOR", "findings": []},
        evidence=[],
        force_run=True,
    )
    assert result.status == EvaluationStatus.FAILED
    assert result.error_message is not None
    assert "failed" in result.summary.lower()


# --------------------------------------------------------------------------- #
# 4. Langfuse Integration Tests (Mocked)
# --------------------------------------------------------------------------- #


def test_record_evaluation_to_langfuse_success() -> None:
    """Emits numerical and categorical scores to Langfuse trace using mock client."""
    mock_lf = MagicMock()

    scores = EvaluationScores(
        evidence_grounding=5,
        reasoning_quality=4,
        investigation_completeness=4,
        report_quality=5,
        overall_quality=4,
    )
    det = DeterministicValidationResult(passed=True)
    eval_res = InvestigationEvaluationResult(
        investigation_id="INV-LF-01",
        trace_id="trace-abc-123",
        status=EvaluationStatus.COMPLETED,
        scores=scores,
        dimension_explanations={"evidence_grounding": "Perfect alignment"},
        deterministic_validation=det,
        human_review_required=False,
    )

    success = record_evaluation_to_langfuse(eval_res, trace_id="trace-abc-123", client=mock_lf)
    assert success is True
    assert eval_res.trace_url is not None
    assert "trace-abc-123" in eval_res.trace_url

    # Verify score method calls
    score_names = [call.kwargs.get("name") for call in mock_lf.score.call_args_list]
    assert "evidence_grounding" in score_names
    assert "reasoning_quality" in score_names
    assert "investigation_completeness" in score_names
    assert "report_quality" in score_names
    assert "overall_quality" in score_names
    assert "deterministic_validation" in score_names
    assert "human_review_required" in score_names


def test_record_evaluation_to_langfuse_creates_dedicated_trace_when_none_provided() -> None:
    """Creates a dedicated trace via lf.trace() when trace_id is omitted."""
    mock_lf = MagicMock()
    mock_trace = MagicMock()
    mock_trace.id = "auto-created-trace-uuid"
    mock_trace.get_trace_url.return_value = "http://localhost:3000/trace/auto-created-trace-uuid"
    mock_lf.trace.return_value = mock_trace

    eval_res = InvestigationEvaluationResult(
        investigation_id="INV-LF-AUTO",
        trace_id=None,
        status=EvaluationStatus.COMPLETED,
        scores=EvaluationScores(overall_quality=5),
    )
    success = record_evaluation_to_langfuse(eval_res, trace_id=None, client=mock_lf)
    assert success is True
    assert eval_res.trace_id == "auto-created-trace-uuid"
    assert "auto-created-trace-uuid" in eval_res.trace_url
    mock_lf.trace.assert_called_once()


def test_record_evaluation_to_langfuse_skipped_when_no_trace_id() -> None:
    """Gracefully returns False when no trace_id is available without raising."""
    eval_res = InvestigationEvaluationResult(
        investigation_id="INV-LF-02",
        trace_id=None,
        status=EvaluationStatus.COMPLETED,
        scores=EvaluationScores(),
    )
    assert record_evaluation_to_langfuse(eval_res, trace_id=None) is False


def test_record_evaluation_to_langfuse_records_failure_status() -> None:
    """When an evaluation has FAILED status, emits evaluation_status=FAILED to trace."""
    mock_lf = MagicMock()
    eval_res = InvestigationEvaluationResult(
        investigation_id="INV-LF-03",
        trace_id="trace-fail-999",
        status=EvaluationStatus.FAILED,
        scores=EvaluationScores(),
        error_message="Judge provider timed out",
    )

    success = record_evaluation_to_langfuse(eval_res, trace_id="trace-fail-999", client=mock_lf)
    assert success is True
    mock_lf.score.assert_called_once()
    assert mock_lf.score.call_args.kwargs.get("name") == "evaluation_status"
    assert mock_lf.score.call_args.kwargs.get("value") == "FAILED"


# --------------------------------------------------------------------------- #
# 5. Benchmark Dataset & Runner Tests
# --------------------------------------------------------------------------- #


def test_benchmark_scenarios_suite_integrity() -> None:
    """Asserts that all 8 required canonical benchmark scenarios are populated correctly."""
    scenarios = get_benchmark_scenarios()
    assert len(scenarios) == 8

    scenario_ids = [s.scenario_id for s in scenarios]
    assert "SCENARIO_1_SUSPICIOUS_CORROBORATED" in scenario_ids
    assert "SCENARIO_2_LEGITIMATE_CLEAN" in scenario_ids
    assert "SCENARIO_3_FABRICATED_TXN_ID" in scenario_ids
    assert "SCENARIO_4_INCORRECT_AMOUNT" in scenario_ids
    assert "SCENARIO_5_INCOMPLETE_EVIDENCE" in scenario_ids
    assert "SCENARIO_6_INCORRECT_RELATIONSHIP" in scenario_ids
    assert "SCENARIO_7_WEAK_REASONING" in scenario_ids
    assert "SCENARIO_8_WELL_GROUNDED_CAUTIOUS" in scenario_ids

    # Each scenario must have valid structure
    for s in scenarios:
        assert s.investigation_id
        assert s.transaction_id
        assert s.report
        assert isinstance(s.evidence, list)


@pytest.mark.asyncio
async def test_benchmark_runner_catches_all_deliberate_errors() -> None:
    """Asserts that BenchmarkRunner catches 100% of deliberate defects and reports 0 false passes."""
    runner = BenchmarkRunner(judge_provider=FakeJudgeLLMProvider())
    report = await runner.run()

    assert report.total_scenarios == 8
    assert report.completed_scenarios == 8
    assert report.failed_scenarios == 0
    assert report.completion_rate_pct == 100.0
    assert report.total_deliberate_error_scenarios == 5
    assert report.deliberate_errors_detected == 5
    assert report.error_detection_rate_pct == 100.0
    assert report.false_passes == 0
    assert report.false_flags == 0
    assert 1.0 <= report.average_scores["overall_quality"] <= 5.0


# --------------------------------------------------------------------------- #
# 6. FastAPI Router Endpoints Tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_api_evaluations_evaluate_endpoint() -> None:
    """Tests POST /api/v1/evaluations/evaluate with FastAPI test client."""
    import httpx
    from apps.api.main import app
    from infrastructure.security.jwt_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "compliance_test",
        "role": "INVESTIGATOR",
    }
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/evaluations/evaluate",
                json={
                    "investigation_id": "INV-API-TEST",
                    "report": {
                        "summary": "Transfer verified against history.",
                        "findings": [{"finding": "Verified", "evidence_ids": ["EV-01"]}],
                        "recommended_action": "CLOSE_NO_ACTION",
                    },
                    "evidence": [{"evidence_id": "EV-01", "reference": "TXN-01"}],
                    "context": {"transaction_id": "TXN-01"},
                    "force_run": True,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["scores"]["overall_quality"] is not None
            assert "deterministic_validation" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_api_evaluations_benchmark_endpoints() -> None:
    """Tests GET /api/v1/evaluations/benchmark/scenarios and POST /api/v1/evaluations/benchmark/run."""
    import httpx
    from apps.api.main import app
    from infrastructure.security.jwt_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "compliance_test",
        "role": "INVESTIGATOR",
    }
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Scenarios endpoint
            resp_sc = await client.get("/api/v1/evaluations/benchmark/scenarios")
            assert resp_sc.status_code == 200
            scenarios = resp_sc.json()
            assert len(scenarios) == 8

            # 2. Run benchmark endpoint
            resp_run = await client.post("/api/v1/evaluations/benchmark/run")
            assert resp_run.status_code == 200
            report = resp_run.json()
            assert report["total_scenarios"] == 8
            assert report["completion_rate_pct"] == 100.0
            assert report["error_detection_rate_pct"] == 100.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
