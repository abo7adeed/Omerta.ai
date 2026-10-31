"""Scoring rubrics and dimension definitions for Omerta.ai LLM-as-a-Judge."""

RUBRIC_EVIDENCE_GROUNDING = """
Dimension 1: Evidence Grounding (Scale: 1-5 or null)
Focus: Evaluates whether claims, transaction IDs, account IDs, amounts, dates, and device signals match the provided verified evidence.
- 5 (Perfect Grounding): Every finding and statement is completely corroborated by database facts, graph intelligence, or verified evidence items. Transaction IDs, account IDs, currencies, dates, and amounts match exactly. Zero hallucinations or fabricated entities.
- 4 (Strong Grounding): Claims are supported by evidence; minor non-substantive detail omitted or minor phrasing ambiguity that does not affect facts.
- 3 (Partial Grounding): Most facts are accurate, but some claims lack explicit evidence citations or contain unverified inferences stated as fact.
- 2 (Poor Grounding): Significant factual inaccuracies, misattributed accounts/transactions, or statements that directly contradict provided evidence.
- 1 (Severe Hallucination / Fabricated Evidence): Contains fabricated transactions, invented account identifiers, hallucinated balances/amounts, or claims with zero evidential basis.
- null: Cannot be evaluated if no evidence was supplied or report is empty.
"""

RUBRIC_REASONING_QUALITY = """
Dimension 2: Reasoning Quality (Scale: 1-5 or null)
Focus: Evaluates logical progression, causality vs correlation, and separation of facts from hypotheses.
- 5 (Airtight Logic): Logical chain flows flawlessly from observed facts. Clearly distinguishes hard evidence (e.g. ledger entries) from structural signals (e.g. graph neighbors) and rule alerts. Does not mistake correlation for proven causation.
- 4 (Sound Reasoning): Coherent and logical analysis; minor minor reasoning step could be explained more thoroughly, but conclusion is well-grounded.
- 3 (Fair Reasoning): Generally plausible, but occasionally leaps to conclusions, over-interprets minor signals, or blurs hypotheses with proven facts.
- 2 (Flawed Reasoning): Serious non-sequiturs, assumes guilt based merely on an alert or association, or treats structural graph proximity as definitive proof of crime.
- 1 (Irrational / Contradictory): Incoherent, internally contradictory, or completely detached from investigative reasoning standards.
- null: Cannot be evaluated if report contains no reasoning or explanation.
"""

RUBRIC_INVESTIGATION_COMPLETENESS = """
Dimension 3: Investigation Completeness (Scale: 1-5 or null)
Focus: Evaluates whether relevant evidence sources (ledger, graph, risk, device/IP, rules) were addressed and whether gaps/unknowns are disclosed.
IMPORTANT: Do NOT penalize an investigation for missing information that was unavailable, not retrieved, or irrelevant to the case.
- 5 (Thorough & Transparent): Addresses all available and relevant investigative dimensions. Explicitly identifies unanswered questions, data limitations, or missing context.
- 4 (Comprehensive): Covers the primary investigative angles; minor relevant context omitted without compromising findings.
- 3 (Moderate Completeness): Covers the immediate transaction or account, but overlooks a key available signal (e.g. ignoring graph connections or device velocity).
- 2 (Superficial): Misses major relevant context available in the evidence; ignores obvious warning signs or fails to investigate immediate counterparties.
- 1 (Grossly Incomplete): Merely repeats the input query without examining the collected evidence tiers.
- null: Cannot be evaluated if scope of investigation is undefined.
"""

RUBRIC_REPORT_QUALITY = """
Dimension 4: Report Quality (Scale: 1-5 or null)
Focus: Evaluates clarity, structure, and professional utility for a human compliance officer/FIU analyst.
- 5 (Exemplary Compliance Report): Highly professional, structured, concise executive summary, explicit risk level, actionable recommended action, and clear evidence citations conforming to Omerta report schema.
- 4 (Clear & Actionable): Well-structured, readable, clear guidance for the compliance officer with minor formatting or verbosity flaws.
- 3 (Acceptable): Understandable, but lacks crisp executive synthesis or has vague recommendations (e.g. "look into it further").
- 2 (Substandard): Disorganized, verbose, repetitive, or missing key report sections.
- 1 (Unusable): Incomprehensible, broken format, or fails to deliver actionable compliance findings.
- null: Cannot be evaluated if report is completely missing.
"""

RUBRIC_OVERALL_QUALITY = """
Dimension 5: Overall Quality (Scale: 1-5 or null)
Focus: Holistic synthesis of the four criteria.
- 5 (Production Grade): An exemplary AML investigation that can be confidently reviewed and actioned by compliance officers.
- 4 (High Quality): Solid, dependable investigation with minor non-critical areas for improvement.
- 3 (Adequate): Requires caution; human analyst must verify several points before making a filing decision.
- 2 (Deficient): Major flaws in grounding, logic, or completeness; unreliable without significant human rework.
- 1 (Rejected): Completely unreliable, hallucinated, or defective.
"""

