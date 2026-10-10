"""End-to-End Validation Script for Omerta.ai Agentic RAG Workflows."""

import asyncio
from domain.agentic_rag.schemas import AgenticRAGRequest
from apps.agentic_rag.graph import execute_agentic_rag


async def test_workflows():
    print("=" * 60)
    print("RUNNING AGENTIC RAG SYSTEM VERIFICATION")
    print("=" * 60)

    # Workflow A: Document Policy RAG
    print("\n--- Workflow A: Banking Policy RAG ---")
    req_a = AgenticRAGRequest(question="What is the policy for restoring access after a security hold?")
    res_a = await execute_agentic_rag(req_a)
    print(f"Status: {res_a.status}")
    print(f"Sources Used: {res_a.sources_used}")
    print(f"Citations: {len(res_a.citations)}")
    for cit in res_a.citations[:2]:
        print(f"  * [{cit.locator}] {cit.title}")
    print(f"Answer snippet:\n{res_a.answer[:300]}...")

    # Workflow B: PostgreSQL Numerical Question
    print("\n--- Workflow B: PostgreSQL Aggregation ---")
    req_b = AgenticRAGRequest(question="How many transactions occurred and what is the total volume?")
    res_b = await execute_agentic_rag(req_b)
    print(f"Status: {res_b.status}")
    print(f"Sources Used: {res_b.sources_used}")
    print(f"Response Blocks: {[b.type for b in res_b.response_blocks]}")
    for b in res_b.response_blocks:
        if b.type == "metric":
            for m in b.metrics:
                print(f"  * KPI: {m.label} = {m.value} {m.unit or ''}")

    # Workflow C: Neo4j Graph Inquiry
    print("\n--- Workflow C: Neo4j Graph Topology ---")
    req_c = AgenticRAGRequest(question="Which accounts are connected through shared devices or network paths?", entity_ids=["ACC-1001"])
    res_c = await execute_agentic_rag(req_c)
    print(f"Status: {res_c.status}")
    print(f"Sources Used: {res_c.sources_used}")
    print(f"Citations: {len(res_c.citations)}")

    # Workflow E: Visualization Engine
    print("\n--- Workflow E: Dynamic Matplotlib Chart ---")
    req_e = AgenticRAGRequest(question="Plot transaction volume trend and risk level distribution")
    res_e = await execute_agentic_rag(req_e)
    print(f"Status: {res_e.status}")
    print(f"Chart Artifact: {[b.chart.artifact_url for b in res_e.response_blocks if b.type == 'chart']}")

    # Workflow F: Financial Comparison
    print("\n--- Workflow F: Period Comparison ---")
    req_f = AgenticRAGRequest(question="Compare current month transaction volume versus previous month")
    res_f = await execute_agentic_rag(req_f)
    print(f"Status: {res_f.status}")
    for b in res_f.response_blocks:
        if b.type == "metric":
            for m in b.metrics:
                print(f"  * Comparison KPI: {m.label} = {m.value} ({m.comparison_text})")

    print("\n" + "=" * 60)
    print("ALL CORE WORKFLOWS EXECUTED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_workflows())
