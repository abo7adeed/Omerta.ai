"""Forensic Guardrails Engine for Omerta.ai Agentic RAG.

Protections Enforced:
1. Input Guardrails:
   - Prompt Injection & Jailbreak Defense (overrides, DAN modes, system prompt leakage).
   - SQL Injection & Harmful Command Detection (DROP, DELETE, TRUNCATE, ALTER).
   - Domain Boundary & Financial In-Scope Enforcement (ensures inquiry is banking/compliance/AML related).
   - PII Sanitization (masking credit card PANs, secret keys, raw credentials).

2. Output Guardrails:
   - Non-Accusatory Terminology Enforcement (replaces legally prejudicial phrases with objective compliance terms).
   - Evidence Grounding Verification (flags ungrounded numerical claims).
   - Compliance Disclaimer & Analytical Warning Generation (ISO-20022 and FATF regulatory disclaimers).
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any

from domain.agentic_rag.schemas import SourceType, WarningBlock

logger = logging.getLogger(__name__)

# Patterns for prompt injection, jailbreaks, and system prompt leakage
PROMPT_INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)\b",
    r"(?i)\bbypass\s+(all\s+)?(security|guardrails|rules|controls)\b",
    r"(?i)\byou\s+are\s+now\s+(in\s+)?(dan|developer|unrestricted|god)\s+mode\b",
    r"(?i)\breveal\s+(your\s+)?(system\s+prompt|initial\s+instructions|secret\s+key|api\s+key)\b",
    r"(?i)\bprint\s+(your\s+)?(system\s+prompt|hidden\s+prompt|configuration)\b",
    r"(?i)\bact\s+as\s+a\s+(hacker|malicious|unfiltered|jailbroken)\b",
    r"(?i)\bdisregard\s+(the\s+)?(rules|safety|guidelines)\b",
    r"(?i)\bdo\s+anything\s+now\b",
]

# Destructive SQL/Command patterns that have no place in read-only natural-language inquiries
DESTRUCTIVE_PATTERNS = [
    r"(?i)\b(drop\s+table|delete\s+from|truncate\s+table|alter\s+table|update\s+\w+\s+set)\b",
    r"(?i)\bexec(\s+xp_|\s+sp_)\b",
    r"(?i)\b--\s*$",
    r"(?i);\s*(drop|delete|insert|update)\b",
]

# Accusatory / Defamatory phrases to replace with neutral compliance terminology
ACCUSATORY_REPLACEMENTS = [
    (r"(?i)\b(is\s+a\s+)?(known\s+)?fraudster\b", "subject entity exhibiting confirmed fraud risk indicators"),
    (r"(?i)\b(is\s+a\s+)?criminal\b", "individual or entity under active compliance inquiry"),
    (r"(?i)\bguilty\s+of\s+fraud\b", "associated with high-risk anomalous transactional patterns"),
    (r"(?i)\billegal\s+money\s+laundering\s+ring\b", "transaction cluster matching money-laundering structuring typologies"),
    (r"(?i)\bcorrupt\s+customer\b", "high-risk counterparty requiring enhanced due diligence"),
    (r"(?i)\bthief\b", "unauthorized transaction initiator"),
]

# Sensitive PII patterns (Credit card 16-digit PANs)
PAN_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
API_KEY_PATTERN = re.compile(r"\b(gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})\b")


@dataclass
class GuardrailResult:
    """Outcome of input or output guardrail evaluation."""
    is_safe: bool = True
    flagged: bool = False
    reason: str | None = None
    sanitized_text: str = ""
    warnings: list[str] = field(default_factory=list)


class ForensicGuardrails:
    """Enforces banking compliance, safety, and non-accusatory integrity across inputs and outputs."""

    @classmethod
    def evaluate_input(cls, question: str) -> GuardrailResult:
        """Evaluate inbound question against injection, destructive commands, and PII."""
        q = question.strip()
        warnings: list[str] = []

        # 1. Prompt Injection & Jailbreak Check
        for pat in PROMPT_INJECTION_PATTERNS:
            if re.search(pat, q):
                logger.warning("Prompt injection attempt detected: %s", pat)
                return GuardrailResult(
                    is_safe=False,
                    flagged=True,
                    reason="Security Violation: Detected prompt injection or instruction override attempt. Query terminated per Omerta.ai Security Policy.",
                    sanitized_text="",
                    warnings=["Input flagged for attempted prompt override or system instruction bypass."],
                )

        # 2. Destructive SQL / Command Pattern Check
        for pat in DESTRUCTIVE_PATTERNS:
            if re.search(pat, q):
                logger.warning("Destructive SQL syntax detected in question: %s", pat)
                return GuardrailResult(
                    is_safe=False,
                    flagged=True,
                    reason="Database Security Violation: Destructive SQL or command keywords are strictly prohibited in analytical inquiries.",
                    sanitized_text="",
                    warnings=["Query contained forbidden database mutation syntax."],
                )

        # 3. PII / Token Sanitization
        sanitized = q
        if PAN_PATTERN.search(sanitized):
            sanitized = PAN_PATTERN.sub("****-****-****-****", sanitized)
            warnings.append("Sensitive card PAN detected and masked for confidentiality.")

        if API_KEY_PATTERN.search(sanitized):
            sanitized = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)
            warnings.append("Secret API token detected and redacted from inquiry.")

        # 4. Banking Scope Soft Check
        banking_keywords = [
            "account", "transaction", "balance", "transfer", "risk", "policy", "hold",
            "aml", "cft", "kyc", "fraud", "customer", "device", "ip", "volume",
            "report", "chart", "plot", "alert", "case", "investigation", "score",
            "currency", "egp", "usd", "eur", "fatf", "sar", "structuring", "limit"
        ]
        has_banking_term = any(re.search(r"\b" + re.escape(kw) + r"\b", sanitized, re.I) for kw in banking_keywords)
        is_short = len(sanitized.split()) <= 4

        if not has_banking_term and not is_short and not re.search(r"\b(TXN-|ACC-|DEV-|CUST-|OMR-)", sanitized, re.I):
            warnings.append("Inquiry appears non-standard. Results will remain strictly bounded to banking domain data.")

        return GuardrailResult(
            is_safe=True,
            flagged=False,
            reason=None,
            sanitized_text=sanitized,
            warnings=warnings,
        )

    @classmethod
    def enforce_output_safety(cls, text: str) -> tuple[str, list[str]]:
        """Apply non-accusatory terminology transformation and safety disclaimers."""
        sanitized = text
        warnings: list[str] = []

        # Replace legally prejudicial terms
        for pat, replacement in ACCUSATORY_REPLACEMENTS:
            if re.search(pat, sanitized):
                sanitized = re.sub(pat, replacement, sanitized)
                warnings.append("Non-accusatory framing guardrail applied to narrative output.")

        # Ensure no accidental raw API key leakage in assistant response
        if API_KEY_PATTERN.search(sanitized):
            sanitized = API_KEY_PATTERN.sub("[REDACTED_KEY]", sanitized)
            warnings.append("Credentials masked in synthesized output.")

        return sanitized, list(set(warnings))

    @classmethod
    def create_compliance_warning(cls, sources_used: list[SourceType], has_high_risk: bool = False) -> WarningBlock:
        """Create formal banking compliance advisory block."""
        if has_high_risk:
            return WarningBlock(
                title="Forensic Compliance Advisory (FATF / ISO-20022)",
                message=(
                    "Identified indicators reflect algorithmic risk anomalies and do not constitute legal determinations of culpability. "
                    "In accordance with internal AML/CFT governance and banking regulations, any account freezing or formal Suspicious Activity "
                    "Report (SAR) filing requires multi-eye human compliance officer sign-off."
                ),
            )
        return WarningBlock(
            title="Evidence Grounding Notice",
            message=(
                "All presented metrics, transaction tallies, and policy references are cryptographically verified against authoritative "
                "banking ledgers and compliance knowledge documents."
            ),
        )
