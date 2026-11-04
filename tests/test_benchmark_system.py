"""Comprehensive unit and integration test suite for the Omerta.ai Benchmark System.

Covers:
- Model availability catalog and pricing metadata.
- Cost and token estimation calculations.
- Benchmark dataset case structure, agent state conversion, and ground truth.
- Side-by-side benchmark runner execution with identical input guarantee.
- Isolated candidate failure handling (Candidate A error does not impact Candidate B).
- Head-to-head metrics, deltas, and aggregate statistics.
- REST API router endpoints.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from domain.evaluation.benchmark.dataset import BenchmarkCase, get_benchmark_dataset
from domain.evaluation.benchmark.models import (
    BenchmarkModelConfig,
    build_candidate_llm_provider,
    get_available_model_catalog,
)
from domain.evaluation.benchmark.pricing import (
    calculate_cost,
    estimate_tokens,
    get_model_pricing,
)
from domain.evaluation.benchmark.side_by_side import SideBySideBenchmarkRunner
from domain.evaluation.judge_provider import FakeJudgeLLMProvider
from infrastructure.llm.base import LLMResponse


@pytest.fixture(autouse=True)
def _setup_benchmark_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure test runs in deterministic offline mode without live API key dependencies."""
    from infrastructure.config import get_settings

    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    settings = get_settings()
    monkeypatch.setattr(settings, "use_local_llm", False, raising=False)
    monkeypatch.setattr(settings, "omerta_evaluation_provider", "fake", raising=False)
    monkeypatch.setattr(settings, "langfuse_enabled", False, raising=False)


# ==============================================================================
# 1. Pricing & Token Estimation Tests
# ==============================================================================


def test_pricing_registry_known_and_fallback_models() -> None:
    """Pricing registry retrieves known rates and graceful fallback for unknown models."""
    groq_120b = get_model_pricing("openai/gpt-oss-120b")
    assert groq_120b["rates"]["prompt_per_m"] == 0.59
    assert groq_120b["rates"]["completion_per_m"] == 0.79
    assert not groq_120b["is_fallback"]

    fake_pricing = get_model_pricing("fake")
    assert fake_pricing["rates"]["prompt_per_m"] == 0.0
    assert fake_pricing["rates"]["completion_per_m"] == 0.0

    unknown = get_model_pricing("some-custom-proprietary-model")
    assert unknown["is_fallback"]
    assert unknown["rates"]["prompt_per_m"] > 0


def test_calculate_cost_computation() -> None:
    """Cost calculations accurately compute USD cost from token counts."""
    # 1,000,000 prompt tokens @ $0.59 + 1,000,000 completion tokens @ $0.79 = $1.38
    res = calculate_cost("openai/gpt-oss-120b", 1_000_000, 1_000_000)
    assert res["total_cost_usd"] == 1.38
    assert res["prompt_cost_usd"] == 0.59
    assert res["completion_cost_usd"] == 0.79

    # Zero tokens or fake model gives 0.0
    fake_cost = calculate_cost("fake", 5000, 2000)
    assert fake_cost["total_cost_usd"] == 0.0


def test_estimate_tokens_length() -> None:
    """Heuristic token estimation returns reasonable positive counts."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") >= 1
    # ~400 characters should yield ~100 tokens
    text = "A" * 400
    assert 90 <= estimate_tokens(text) <= 110


# ==============================================================================
# 2. Model Catalog & Factory Tests
# ==============================================================================


def test_model_catalog_structure() -> None:
    """Catalog contains recognized models with pricing and status indicators."""
    catalog = get_available_model_catalog()
    assert len(catalog) >= 5

    model_ids = [m.model_id for m in catalog]
    assert "openai/gpt-oss-120b" in model_ids
    assert "openai/gpt-oss-20b" in model_ids
    assert "fake" in model_ids

    fake_info = next(m for m in catalog if m.model_id == "fake")
    assert fake_info.is_available is True
    assert "Always available" in fake_info.status_message


def test_build_candidate_llm_provider_fake() -> None:
    """Provider factory builds deterministic provider for fake config."""
    config = BenchmarkModelConfig(model_id="fake", provider="fake")
    provider = build_candidate_llm_provider(config)
    assert provider.name == "fake"


def test_build_candidate_llm_provider_groq() -> None:
    """Provider factory configures Groq OpenAICompatibleProvider with timeout and tokens."""
    config = BenchmarkModelConfig(
        model_id="openai/gpt-oss-120b",
        provider="groq",
        timeout_seconds=45.0,
        max_tokens=2048,
    )
    provider = build_candidate_llm_provider(config)
    assert provider.name == "groq"
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.base_url == "https://api.groq.com/openai/v1"


# ==============================================================================
# 3. Benchmark Dataset Integrity Tests
# ==============================================================================


def test_benchmark_dataset_canonical_cases() -> None:
    """Dataset v1.0 contains the required 7 canonical test cases."""
    cases = get_benchmark_dataset(version="1.0")
    assert len(cases) == 7

    case_ids = [c.case_id for c in cases]
    assert "CASE-01-CLEAN-COMPLETE" in case_ids
    assert "CASE-02-SUSPICIOUS-CORROBORATED" in case_ids
    assert "CASE-03-UNSUPPORTED-CLAIMS-TRAP" in case_ids
    assert "CASE-04-INCOMPLETE-EVIDENCE" in case_ids
    assert "CASE-05-REGRESSION-SAR-001" in case_ids
    assert "CASE-06-REGRESSION-CLEAN-002" in case_ids
    assert "CASE-07-SCHEMA-STRESS" in case_ids

    # Validate state conversion
    for c in cases:
        state = c.to_agent_state()
        assert state["investigation_id"] == c.investigation_id
        assert state["transaction_id"] == c.transaction_id
        assert isinstance(state["evidence"], list)
        assert len(state["evidence"]) > 0


# ==============================================================================
# 4. Side-by-Side Execution & Statistics Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_side_by_side_runner_deterministic_execution() -> None:
    """Side-by-side runner evaluates candidate models on identical inputs and computes statistics."""
    model_a_cfg = BenchmarkModelConfig(model_id="fake", provider="fake", display_name="Mock A")
    model_b_cfg = BenchmarkModelConfig(model_id="fake", provider="fake", display_name="Mock B")

    runner = SideBySideBenchmarkRunner(judge_provider=FakeJudgeLLMProvider())

    cases = get_benchmark_dataset()[:2]  # run first 2 cases for fast unit test
    result = await runner.run(
        model_a_config=model_a_cfg,
        model_b_config=model_b_cfg,
        cases=cases,
        persist=False,  # unit test without live DB
    )

    assert result["status"] == "COMPLETED"
    assert result["total_cases"] == 2
    assert result["completed_cases"] == 2
    assert len(result["cases"]) == 2

    # Verify candidate A and B results are present
    case_0 = result["cases"][0]
    assert case_0["model_a_status"] == "COMPLETED"
    assert case_0["model_b_status"] == "COMPLETED"
    assert case_0["model_a_validation"]["passed"] is True
    assert case_0["model_b_validation"]["passed"] is True

    # Check differences summary
    diff = case_0["differences_summary"]
    assert "winner" in diff
    assert "score_deltas" in diff

    # Check aggregate metrics
    agg = result["aggregate_metrics"]
    assert agg["total_cases"] == 2
    assert "model_a" in agg
    assert "model_b" in agg
    assert "comparison" in agg
    assert "overall_quality" in agg["model_a"]["average_scores"]
    assert "overall_quality" in agg["model_a"]["median_scores"]


@pytest.mark.asyncio
async def test_failure_isolation_candidate_error() -> None:
    """When Candidate A fails, Candidate B still executes and completes independently."""
    model_a_cfg = BenchmarkModelConfig(model_id="faulty-model", provider="groq")
    model_b_cfg = BenchmarkModelConfig(model_id="fake", provider="fake")

    runner = SideBySideBenchmarkRunner(judge_provider=FakeJudgeLLMProvider())

    # Mock provider_a to raise an exception, provider_b to succeed
    failing_provider = AsyncMock()
    failing_provider.complete.side_effect = RuntimeError("Connection timeout to inference gateway")
    failing_provider.name = "groq"
    failing_provider.model = "faulty-model"

    case = get_benchmark_dataset()[0]

    with patch(
        "domain.evaluation.benchmark.side_by_side.build_candidate_llm_provider"
    ) as mock_builder:
        mock_builder.side_effect = [
            failing_provider,
            build_candidate_llm_provider(model_b_cfg),
        ]

        result = await runner.run(
            model_a_config=model_a_cfg,
            model_b_config=model_b_cfg,
            cases=[case],
            persist=False,
        )

        assert result["status"] == "COMPLETED"
        case_res = result["cases"][0]

        # Candidate A failed gracefully
        assert case_res["model_a_status"] == "FAILED"
        assert "Connection timeout" in case_res["model_a_error"]

        # Candidate B succeeded completely
        assert case_res["model_b_status"] == "COMPLETED"
        assert case_res["model_b_validation"]["passed"] is True
        assert case_res["model_b_evaluation"]["status"] == "completed"

        # Winner was awarded to Model B
        assert case_res["differences_summary"]["winner"] == "MODEL_B"


# ==============================================================================
# 5. REST API Router Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_api_models_endpoint() -> None:
    """GET /api/v1/benchmarks/models returns active catalog."""
    from apps.api.v1.benchmarks import list_models_endpoint

    catalog = await list_models_endpoint(current_user={"sub": "TEST"})
    assert isinstance(catalog, list)
    assert len(catalog) >= 5


@pytest.mark.asyncio
async def test_api_scenarios_endpoint() -> None:
    """GET /api/v1/benchmarks/scenarios returns canonical dataset."""
    from apps.api.v1.benchmarks import list_scenarios_endpoint

    scenarios = await list_scenarios_endpoint(version="1.0", current_user={"sub": "TEST"})
    assert len(scenarios) == 7
    assert scenarios[0].case_id == "CASE-01-CLEAN-COMPLETE"


@pytest.mark.asyncio
async def test_api_execute_run_endpoint() -> None:
    """POST /api/v1/benchmarks/runs executes run with selected case subset."""
    from apps.api.v1.benchmarks import CreateBenchmarkRunRequest, execute_benchmark_run_endpoint

    payload = CreateBenchmarkRunRequest(
        model_a=BenchmarkModelConfig(model_id="fake", provider="fake"),
        model_b=BenchmarkModelConfig(model_id="fake", provider="fake"),
        case_ids=["CASE-01-CLEAN-COMPLETE"],
        dataset_version="1.0",
    )

    with patch.object(SideBySideBenchmarkRunner, "run") as mock_run:
        mock_run.return_value = {
            "run_id": "TEST-RUN-001",
            "status": "COMPLETED",
            "total_cases": 1,
            "completed_cases": 1,
            "aggregate_metrics": {},
            "cases": [],
        }

        res = await execute_benchmark_run_endpoint(payload, current_user={"sub": "TEST"})
        assert res["run_id"] == "TEST-RUN-001"
        assert res["status"] == "COMPLETED"


# ==============================================================================
# 6. Advanced Evaluation & Hardware Metrics Tests
# ==============================================================================


def test_citation_metrics_calculation() -> None:
    """Citation metrics accurately compute citation accuracy and evidence coverage."""
    from domain.evaluation.benchmark.metrics import compute_citation_metrics

    evidence = [
        {"evidence_id": "EV-001", "description": "Txn 1"},
        {"evidence_id": "EV-002", "description": "Txn 2"},
        {"evidence_id": "EV-003", "description": "Txn 3"},
    ]

    report = {
        "findings": [
            {"finding": "Finding 1", "evidence_ids": ["EV-001"]},
            {"finding": "Finding 2", "evidence_ids": ["EV-002", "EV-NONEXISTENT"]},
            {"finding": "Finding 3", "evidence_ids": ["EV-INVALID"]},
        ]
    }

    res = compute_citation_metrics(report, evidence)
    # 2 out of 3 findings have valid evidence -> 66.7%
    assert res["citation_accuracy_pct"] == 66.7
    # 2 out of 3 evidence items cited (EV-001, EV-002) -> 66.7%
    assert res["evidence_coverage_pct"] == 66.7
    assert "EV-NONEXISTENT" in res["invalid_evidence_ids"]
    assert "EV-INVALID" in res["invalid_evidence_ids"]


def test_ground_truth_metrics_calculation() -> None:
    """Ground truth metrics compute precision, recall, and F1."""
    from domain.evaluation.benchmark.metrics import compute_ground_truth_metrics

    ground_truth = {
        "expected_risk_level": "CRITICAL",
        "expected_action": "FILE_SAR",
        "typologies": ["MULE_NETWORK", "STRUCTURING"],
    }

    # Perfect prediction
    report_perfect = {
        "risk_level": "CRITICAL",
        "recommended_action": "FILE_SAR",
        "typologies": ["MULE_NETWORK", "STRUCTURING"],
    }
    res_perf = compute_ground_truth_metrics(report_perfect, ground_truth)
    assert res_perf["precision"] == 1.0
    assert res_perf["recall"] == 1.0
    assert res_perf["f1_score"] == 1.0
    assert res_perf["risk_level_matched"] is True
    assert res_perf["action_matched"] is True

    # Partial prediction: 1 TP (MULE_NETWORK), 1 FP (RAPID_MOVEMENT), 1 FN (STRUCTURING)
    report_partial = {
        "risk_level": "HIGH",
        "recommended_action": "FILE_SAR",
        "typologies": ["MULE_NETWORK", "RAPID_MOVEMENT"],
    }
    res_part = compute_ground_truth_metrics(report_partial, ground_truth)
    assert res_part["precision"] == 0.5
    assert res_part["recall"] == 0.5
    assert res_part["f1_score"] == 0.5
    assert res_part["risk_level_matched"] is False
    assert res_part["action_matched"] is True


def test_latency_distribution_and_p95() -> None:
    """Latency distribution computes correct mean, median, P95, min, and max."""
    from domain.evaluation.benchmark.metrics import compute_latency_distribution

    latencies = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0]
    res = compute_latency_distribution(latencies)

    assert res["min_latency_ms"] == 100.0
    assert res["max_latency_ms"] == 1000.0
    assert res["mean_latency_ms"] == 550.0
    assert res["median_latency_ms"] == 550.0
    assert res["p95_latency_ms"] == 1000.0


def test_cost_projections() -> None:
    """Cost projections calculate per-case and 1,000 cases projections."""
    from domain.evaluation.benchmark.metrics import compute_cost_projections

    # $0.005 total for 2 cases -> $0.0025 per case, $2.50 per 1,000 cases
    res = compute_cost_projections(0.005, 2)
    assert res["cost_per_case_usd"] == 0.0025
    assert res["projected_cost_per_1000_cases_usd"] == 2.50
    assert res["currency"] == "USD"


def test_gpu_vram_profiling_output_structure() -> None:
    """GPU profiling function returns normalized structure even if GPU is absent."""
    from domain.evaluation.benchmark.metrics import get_gpu_vram_usage

    res = get_gpu_vram_usage()
    assert isinstance(res, dict)
    assert "measured" in res
    if res["measured"]:
        assert res["vram_used_mb"] is not None
        assert res["vram_total_mb"] is not None
        assert res["vram_free_mb"] is not None
        assert res["gpu_name"] is not None
    else:
        assert res["reason"] is not None


@pytest.mark.asyncio
async def test_api_export_benchmark_run_json_and_csv() -> None:
    """GET /api/v1/benchmarks/runs/{run_id}/export produces valid JSON and CSV downloads."""
    from apps.api.v1.benchmarks import export_benchmark_run_endpoint
    from infrastructure.database.models import BenchmarkCaseResult, BenchmarkRun

    mock_run = MagicMock(spec=BenchmarkRun)
    mock_run.run_id = "RUN-EXPORT-TEST"
    mock_run.dataset_version = "1.0"
    mock_run.status = "COMPLETED"
    mock_run.model_a_config = {"model_id": "qwen2.5:1.5b", "provider": "ollama"}
    mock_run.model_b_config = {"model_id": "openai/gpt-oss-120b", "provider": "groq"}
    mock_run.judge_config = {"model_id": "openai/gpt-oss-120b"}
    mock_run.total_cases = 1
    mock_run.completed_cases = 1
    mock_run.started_at = datetime.now(UTC)
    mock_run.completed_at = datetime.now(UTC)
    mock_run.aggregate_metrics = {}
    mock_run.pricing_metadata = {}

    mock_case = MagicMock(spec=BenchmarkCaseResult)
    mock_case.case_id = "CASE-01"
    mock_case.scenario_type = "CLEAN"
    mock_case.model_a_status = "COMPLETED"
    mock_case.model_a_latency_ms = 1200.0
    mock_case.model_a_tokens = {"total_tokens": 150}
    mock_case.model_a_cost_usd = 0.0
    mock_case.model_a_validation = {"passed": True}
    mock_case.model_a_evaluation = {"scores": {"overall_quality": 4, "evidence_grounding": 4}}
    mock_case.model_a_metrics = {"citation_metrics": {"citation_accuracy_pct": 100.0, "evidence_coverage_pct": 100.0}}
    mock_case.model_b_status = "COMPLETED"
    mock_case.model_b_latency_ms = 2200.0
    mock_case.model_b_tokens = {"total_tokens": 200}
    mock_case.model_b_cost_usd = 0.0002
    mock_case.model_b_validation = {"passed": True}
    mock_case.model_b_evaluation = {"scores": {"overall_quality": 5, "evidence_grounding": 5}}
    mock_case.model_b_metrics = {"citation_metrics": {"citation_accuracy_pct": 100.0, "evidence_coverage_pct": 100.0}}
    mock_case.differences_summary = {"winner": "MODEL_B"}

    mock_run.cases = [mock_case]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_session.execute.return_value = mock_result

    with patch("apps.api.v1.benchmarks.AsyncSession") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # Test JSON Export
        resp_json = await export_benchmark_run_endpoint(
            run_id="RUN-EXPORT-TEST",
            format="json",
            current_user={"sub": "TEST"},
        )
        assert resp_json.media_type == "application/json"
        data = json.loads(resp_json.body.decode())
        assert data["run_id"] == "RUN-EXPORT-TEST"
        assert len(data["cases"]) == 1

        # Test CSV Export
        resp_csv = await export_benchmark_run_endpoint(
            run_id="RUN-EXPORT-TEST",
            format="csv",
            current_user={"sub": "TEST"},
        )
        assert resp_csv.media_type == "text/csv"
        csv_text = resp_csv.body.decode()
        assert "case_id,scenario_type,winner" in csv_text
        assert "CASE-01,CLEAN,MODEL_B,qwen2.5:1.5b" in csv_text


