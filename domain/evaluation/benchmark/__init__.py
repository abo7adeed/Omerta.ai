"""Omerta.ai AML Evaluation & Model Benchmarking Suite."""

from domain.evaluation.benchmark.dataset import BenchmarkCase, get_benchmark_dataset
from domain.evaluation.benchmark.models import (
    BenchmarkModelConfig,
    ModelAvailabilityInfo,
    build_candidate_llm_provider,
    get_available_model_catalog,
)
from domain.evaluation.benchmark.pricing import calculate_cost, estimate_tokens, get_model_pricing
from domain.evaluation.benchmark.runner import BenchmarkRunReport, BenchmarkRunner, ScenarioEvaluationRecord
from domain.evaluation.benchmark.scenarios import BenchmarkScenario, get_benchmark_scenarios
from domain.evaluation.benchmark.side_by_side import SideBySideBenchmarkRunner

__all__ = [
    "BenchmarkCase",
    "BenchmarkModelConfig",
    "BenchmarkRunReport",
    "BenchmarkRunner",
    "BenchmarkScenario",
    "ModelAvailabilityInfo",
    "ScenarioEvaluationRecord",
    "SideBySideBenchmarkRunner",
    "build_candidate_llm_provider",
    "calculate_cost",
    "estimate_tokens",
    "get_available_model_catalog",
    "get_benchmark_dataset",
    "get_benchmark_scenarios",
    "get_model_pricing",
]
