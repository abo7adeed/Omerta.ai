#!/usr/bin/env python
"""CLI runner for Omerta.ai LLM-as-a-Judge Evaluation Benchmark.

Usage:
    # Run using configured provider in .env (Groq API):
    python scripts/run_evaluation_benchmark.py

    # Override to specific Groq model:
    python scripts/run_evaluation_benchmark.py --provider groq --model openai/gpt-oss-120b

    # Run offline with deterministic fake provider:
    python scripts/run_evaluation_benchmark.py --force-fake
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.evaluation.benchmark import BenchmarkRunner
from domain.evaluation.judge_provider import get_judge_llm_provider
from infrastructure.config import get_settings


async def main() -> None:
    # Ensure Windows console supports full UTF-8
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Run Omerta.ai AML Evaluation Benchmark")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="benchmark_results.json",
        help="Path to save the structured JSON benchmark results (default: benchmark_results.json)",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=None,
        help="Override judge provider (e.g. groq, openai, ollama, fake)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Override judge model (e.g. openai/gpt-oss-120b, openai/gpt-oss-20b)",
    )
    parser.add_argument(
        "--force-fake",
        action="store_true",
        help="Force deterministic offline fake judge provider regardless of .env configuration",
    )
    args = parser.parse_args()

    settings = get_settings()
    provider = get_judge_llm_provider(
        force_fake=args.force_fake,
        provider_override=args.provider,
        model_override=args.model,
    )

    print("==================================================================")
    print("           Omerta.ai LLM-as-a-Judge Benchmark Suite              ")
    print("==================================================================")
    print(f" Judge Provider: {getattr(provider, 'name', 'unknown')}")
    print(f" Judge Model:    {getattr(provider, 'model', 'unknown')}")
    print(f" Eval Version:   {settings.omerta_evaluation_version}")
    print(f" Output File:    {args.output}")
    print("------------------------------------------------------------------")

    runner = BenchmarkRunner(judge_provider=provider)
    report = await runner.run(output_path=args.output)

    print("\n================== BENCHMARK EXECUTION RESULTS ==================")
    print(f" Total Scenarios:        {report.total_scenarios}")
    print(f" Completed:              {report.completed_scenarios}")
    print(f" Failed:                 {report.failed_scenarios}")
    print(f" Completion Rate:        {report.completion_rate_pct:.1f}%")
    print(f" Total Execution Time:   {report.total_latency_ms:.1f} ms")
    print(f" Average Latency:        {report.average_latency_ms:.1f} ms / scenario")
    print("\n--- Dimension Averages (1-5 Scale) ---")
    for dim, avg in report.average_scores.items():
        print(f"  * {dim.replace('_', ' ').title():<28}: {avg:.2f} / 5.00")

    print("\n--- Deliberate Error Detection Performance ---")
    print(f"  * Error Scenarios Tested: {report.total_deliberate_error_scenarios}")
    print(f"  * Errors Caught:          {report.deliberate_errors_detected} / {report.total_deliberate_error_scenarios}")
    print(f"  * Detection Accuracy:     {report.error_detection_rate_pct:.1f}%")
    print(f"  * False Passes (Misses):  {report.false_passes}")
    print(f"  * False Flags:            {report.false_flags}")

    print("\n--- Granular Scenario Breakdown ---")
    for rec in report.records:
        status_flag = "PASS" if not rec.has_deliberate_error or rec.detected_deliberate_error else "FAIL"
        err_info = f" [Defect: {rec.error_type}]" if rec.has_deliberate_error else " [Clean]"
        print(
            f"  [{status_flag}] {rec.scenario_id:<32} "
            f"Overall={rec.scores.get('overall_quality', '-')}/5 "
            f"Grounding={rec.scores.get('evidence_grounding', '-')}/5 "
            f"{err_info}"
        )

    print("\n" + report.disclaimer)
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
