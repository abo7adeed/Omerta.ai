"""Side-by-side experiment runner: Local Ollama Model vs Existing Cloud Model.

Runs identical AML investigation scenarios against both the local model
(e.g., Ollama qwen3.5:4b) and the existing cloud model (e.g., Groq),
measuring latency, schema validity, evidence grounding, and economic cost.

Usage:
    # Run comparison on default scenarios:
    python scripts/compare_llm_experiment.py

    # Compare against a specific local model tag:
    python scripts/compare_llm_experiment.py --local-model qwen2.5:1.5b

    # Compare on a specific scenario:
    python scripts/compare_llm_experiment.py --scenario TXN-001
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

from infrastructure.config import get_settings
from infrastructure.llm.factory import get_llm_provider
from scripts.evaluate_investigator import SCENARIOS, evaluate


async def _run_with_provider(transaction_id: str, provider) -> dict[str, Any]:
    from apps.investigator.graph import run_investigation_async
    from infrastructure.database.session import create_engine, use_engine
    import apps.investigator.agent as agent_module

    # Inject target provider for this test
    original_get_provider = agent_module.get_llm_provider
    agent_module.get_llm_provider = lambda: provider

    started = time.perf_counter()
    engine = create_engine(use_null_pool=True)
    try:
        with use_engine(engine):
            final = await run_investigation_async(transaction_id)
    finally:
        agent_module.get_llm_provider = original_get_provider
        await engine.dispose()

    result = evaluate(final, transaction_id)
    result["wall_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return result


async def run_experiment(
    scenarios: list[str],
    local_model: str,
    local_base_url: str,
    cloud_provider_name: str | None = None,
) -> None:
    settings = get_settings()

    # 1. Build Local Provider
    local_provider = get_llm_provider(force_local=True)
    # 2. Build Cloud Provider (existing running model)
    cloud_provider = get_llm_provider(force_local=False)

    print("=" * 80)
    print(" OMBERTA.AI — LOCAL VS CLOUD LLM EXPERIMENT BENCHMARK")
    print("=" * 80)
    print(f" Local Model   : {local_provider.name} | {local_provider.model} ({local_base_url})")
    print(f" Existing Model: {cloud_provider.name} | {cloud_provider.model}")
    print(f" Scenarios     : {', '.join(scenarios)}")
    print("=" * 80)
    print()

    results = []

    for sc in scenarios:
        print(f"--> Running Scenario [{sc}] on Local Model ({local_provider.model})...")
        try:
            local_res = await _run_with_provider(sc, local_provider)
            local_res["mode"] = "LOCAL"
            local_res["cost"] = "$0.0000"
            results.append(local_res)
        except Exception as e:
            print(f"    [!] Local run failed: {e}")
            results.append({
                "scenario": sc,
                "mode": "LOCAL",
                "provider": "ollama",
                "model": local_model,
                "status": f"FAILED ({type(e).__name__})",
                "findings": 0,
                "grounding_violations": [str(e)],
                "action": "ERROR",
                "risk_level": "ERROR",
                "wall_ms": 0.0,
                "cost": "$0.0000",
            })

        print(f"--> Running Scenario [{sc}] on Cloud Model ({cloud_provider.model})...")
        try:
            cloud_res = await _run_with_provider(sc, cloud_provider)
            cloud_res["mode"] = "CLOUD"
            cloud_res["cost"] = "~$0.0016"
            results.append(cloud_res)
        except Exception as e:
            print(f"    [!] Cloud run failed: {e}")
            results.append({
                "scenario": sc,
                "mode": "CLOUD",
                "provider": cloud_provider.name,
                "model": cloud_provider.model,
                "status": f"FAILED ({type(e).__name__})",
                "findings": 0,
                "grounding_violations": [str(e)],
                "action": "ERROR",
                "risk_level": "ERROR",
                "wall_ms": 0.0,
                "cost": "$0.0000",
            })

    print()
    print("=" * 88)
    print(f"{'Mode':<7} {'Scenario':<10} {'Model':<20} {'Status':<10} {'Find':<5} {'Grounding':<10} {'Action':<15} {'Latency':<9} {'Cost':<8}")
    print("=" * 88)

    for r in results:
        grounding = "OK (0)" if not r["grounding_violations"] else f"ERR ({len(r['grounding_violations'])})"
        print(
            f"{r['mode']:<7} {r['scenario']:<10} {r['model']:<20} {r['status']:<10} "
            f"{r['findings']:<5} {grounding:<10} {r['action']:<15} {r['wall_ms']}ms   {r['cost']:<8}"
        )

    print("=" * 88)
    print("\n[+] Experiment complete! You can switch the entire application between Local & Cloud")
    print("    anytime by setting USE_LOCAL_LLM=true or false in your .env file.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", "-s", help="Single scenario to test (e.g. TXN-001)")
    parser.add_argument("--local-model", default="qwen3.5:4b", help="Ollama model tag (default: qwen3.5:4b)")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="Ollama API base URL")

    args = parser.parse_args()
    scenarios = [args.scenario] if args.scenario else SCENARIOS

    os.environ["OLLAMA_MODEL"] = args.local_model
    os.environ["OLLAMA_BASE_URL"] = args.base_url

    asyncio.run(
        run_experiment(
            scenarios=scenarios,
            local_model=args.local_model,
            local_base_url=args.base_url,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
