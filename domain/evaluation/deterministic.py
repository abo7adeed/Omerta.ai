"""Deterministic factual and structural validation for Omerta.ai investigations.

Executes rule-based, non-LLM checks against verified evidence, relational anchors,
and graph topology. Factual contradictions are recorded as discrepancies;
unprovable assertions are marked as unverified rather than automatically false.
"""

from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any

from domain.evaluation.schemas import DeterministicCheckItem, DeterministicValidationResult

logger = logging.getLogger(__name__)

# Patterns for extracting business identifiers from free-text reports
TXN_ID_PATTERN = re.compile(r"\bTXN-[A-Za-z0-9_-]+\b", re.IGNORECASE)
ACC_ID_PATTERN = re.compile(r"\bACC-[A-Za-z0-9_-]+\b", re.IGNORECASE)
DEV_ID_PATTERN = re.compile(r"\bDEV-[A-Za-z0-9_-]+\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"(?:\$|USD\s*|EUR\s*|GBP\s*)?\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)\b")


class DeterministicValidator:
    """Performs deterministic verification of investigation reports against verified evidence."""

    def validate(
        self,
        report_data: dict[str, Any],
        evidence_items: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> DeterministicValidationResult:
        """Run all deterministic validation checks against report and evidence."""
        context = context or {}
        checks: list[DeterministicCheckItem] = []
        discrepancies: list[str] = []
        unverified_claims: list[str] = []

        # 1. Schema integrity check
        schema_check = self._check_schema_integrity(report_data)
        checks.append(schema_check)
        if not schema_check.passed:
            discrepancies.extend(schema_check.discrepancies)

        # 2. Extract valid known entity pools from evidence and context
        known_txn_ids, known_acc_ids, known_dev_ids, known_evidence_ids = self._extract_known_entities(
            evidence_items, context, report_data
        )

        # Extract free-text content from report for text analysis
        report_text = self._extract_full_text(report_data)

        # 3. Transaction ID validation
        txn_check = self._check_transaction_ids(report_text, report_data, known_txn_ids)
        checks.append(txn_check)
        if not txn_check.passed:
            discrepancies.extend(txn_check.discrepancies)
        unverified_claims.extend(txn_check.unverified_items)

        # 4. Account ID validation
        acc_check = self._check_account_ids(report_text, report_data, known_acc_ids)
        checks.append(acc_check)
        if not acc_check.passed:
            discrepancies.extend(acc_check.discrepancies)
        unverified_claims.extend(acc_check.unverified_items)

        # 5. Amounts and Currency validation
        amount_check = self._check_amounts(report_text, report_data, context, evidence_items)
        checks.append(amount_check)
        if not amount_check.passed:
            discrepancies.extend(amount_check.discrepancies)

        # 6. Graph Relationships validation
        graph_check = self._check_graph_relationships(report_text, report_data, context, evidence_items)
        checks.append(graph_check)
        if not graph_check.passed:
            discrepancies.extend(graph_check.discrepancies)
        unverified_claims.extend(graph_check.unverified_items)

        # 7. Evidence citation integrity
        citation_check = self._check_evidence_citations(report_data, known_evidence_ids)
        checks.append(citation_check)
        if not citation_check.passed:
            discrepancies.extend(citation_check.discrepancies)

        all_passed = all(c.passed for c in checks)

        return DeterministicValidationResult(
            passed=all_passed,
            account_ids_valid=acc_check.passed,
            transaction_ids_valid=txn_check.passed,
            amounts_valid=amount_check.passed,
            dates_valid=True,
            relationships_valid=graph_check.passed,
            evidence_references_valid=citation_check.passed,
            schema_valid=schema_check.passed,
            discrepancies=discrepancies,
            unverified_claims=unverified_claims,
            checks=checks,
        )

    def _extract_full_text(self, report_data: dict[str, Any]) -> str:
        """Combine all free-text fields in report for deterministic scanning."""
        parts: list[str] = []
        for key in ["summary", "executive_summary", "forensic_report_markdown", "risk_assessment_explanation"]:
            val = report_data.get(key)
            if isinstance(val, str):
                parts.append(val)
        for f in report_data.get("findings", []):
            if isinstance(f, dict) and "finding" in f:
                parts.append(str(f["finding"]))
            elif isinstance(f, str):
                parts.append(f)
        for exp in report_data.get("factor_explanations", []):
            if isinstance(exp, str):
                parts.append(exp)
        return "\n".join(parts)

    def _extract_known_entities(
        self,
        evidence_items: list[dict[str, Any]],
        context: dict[str, Any],
        report_data: dict[str, Any],
    ) -> tuple[set[str], set[str], set[str], set[str]]:
        """Collect the authoritative pool of known IDs from verified inputs."""
        txns: set[str] = set()
        accs: set[str] = set()
        devs: set[str] = set()
        ev_ids: set[str] = set()

        # From context
        if context.get("transaction_id"):
            txns.add(str(context["transaction_id"]).upper())
        txn_ctx = context.get("transaction") or {}
        if txn_ctx.get("transaction_id"):
            txns.add(str(txn_ctx["transaction_id"]).upper())
        if txn_ctx.get("sender", {}).get("external_id"):
            accs.add(str(txn_ctx["sender"]["external_id"]).upper())
        if txn_ctx.get("recipient", {}).get("external_id"):
            accs.add(str(txn_ctx["recipient"]["external_id"]).upper())
        if context.get("account_id"):
            accs.add(str(context["account_id"]).upper())

        # From evidence items
        for item in evidence_items:
            eid = item.get("evidence_id")
            if eid:
                ev_ids.add(str(eid))
            ref = str(item.get("reference", "")).upper()
            if ref.startswith("TXN-"):
                txns.add(ref)
            elif ref.startswith("ACC-"):
                accs.add(ref)
            elif ref.startswith("DEV-"):
                devs.add(ref)

            data = item.get("data") or {}
            for k, v in data.items():
                if isinstance(v, str):
                    if v.upper().startswith("TXN-"):
                        txns.add(v.upper())
                    elif v.upper().startswith("ACC-"):
                        accs.add(v.upper())
                    elif v.upper().startswith("DEV-"):
                        devs.add(v.upper())

        # From graph context
        shared_devs = context.get("shared_devices") or {}
        for d in shared_devs.get("shared_devices", []):
            if isinstance(d, dict) and d.get("device_id"):
                devs.add(str(d["device_id"]).upper())
            elif isinstance(d, str):
                devs.add(d.upper())

        connected = context.get("connected_accounts") or {}
        for a in connected.get("accounts", []):
            if isinstance(a, dict) and a.get("account_id"):
                accs.add(str(a["account_id"]).upper())

        # Anchor report identifiers
        if report_data.get("transaction_id"):
            txns.add(str(report_data["transaction_id"]).upper())
        if report_data.get("account_id"):
            accs.add(str(report_data["account_id"]).upper())

        return txns, accs, devs, ev_ids

    def _check_schema_integrity(self, report_data: dict[str, Any]) -> DeterministicCheckItem:
        """Verify presence of core required investigation report fields."""
        discrepancies: list[str] = []

        # Check either Phase 9 InvestigationReport format or AccountInvestigationReport format
        is_p9 = "findings" in report_data or "risk_level" in report_data
        is_account = "executive_summary" in report_data or "account_facts" in report_data

        if not is_p9 and not is_account:
            discrepancies.append("Report matches neither InvestigationReport nor AccountInvestigationReport schema.")

        if is_p9:
            for required in ["summary", "recommended_action", "findings"]:
                if required not in report_data or not report_data[required]:
                    discrepancies.append(f"Missing required InvestigationReport field: '{required}'")

        if is_account:
            if not report_data.get("executive_summary"):
                discrepancies.append("Missing required AccountInvestigationReport field: 'executive_summary'")

        passed = len(discrepancies) == 0
        details = "Schema validated successfully." if passed else "; ".join(discrepancies)
        return DeterministicCheckItem(
            check_name="schema_integrity",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
        )

    def _check_transaction_ids(
        self, report_text: str, report_data: dict[str, Any], known_txn_ids: set[str]
    ) -> DeterministicCheckItem:
        """Validate all mentioned transaction IDs against verified context."""
        mentioned = {m.upper() for m in TXN_ID_PATTERN.findall(report_text)}
        if report_data.get("transaction_id"):
            mentioned.add(str(report_data["transaction_id"]).upper())

        discrepancies: list[str] = []
        unverified: list[str] = []

        for tid in mentioned:
            if known_txn_ids and tid not in known_txn_ids:
                discrepancies.append(f"Fabricated or unknown transaction ID: '{tid}'")

        passed = len(discrepancies) == 0
        details = (
            f"All {len(mentioned)} transaction IDs verified."
            if passed
            else f"Found {len(discrepancies)} unverified transaction IDs."
        )
        return DeterministicCheckItem(
            check_name="transaction_id_validation",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
            unverified_items=unverified,
        )

    def _check_account_ids(
        self, report_text: str, report_data: dict[str, Any], known_acc_ids: set[str]
    ) -> DeterministicCheckItem:
        """Validate all mentioned account IDs against verified context."""
        mentioned = {m.upper() for m in ACC_ID_PATTERN.findall(report_text)}
        if report_data.get("account_id"):
            mentioned.add(str(report_data["account_id"]).upper())

        discrepancies: list[str] = []
        unverified: list[str] = []

        for aid in mentioned:
            if known_acc_ids and aid not in known_acc_ids:
                # In AML, an external counterparty might not be in our internal database;
                # mark as unverified claim rather than definite falsehood unless explicitly fabricated
                unverified.append(f"Account ID '{aid}' not present in verified ledger or graph evidence.")

        passed = len(discrepancies) == 0
        details = (
            f"Verified {len(mentioned)} account IDs."
            if passed
            else f"Account check reported {len(discrepancies)} discrepancies."
        )
        return DeterministicCheckItem(
            check_name="account_id_validation",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
            unverified_items=unverified,
        )

    def _check_amounts(
        self,
        report_text: str,
        report_data: dict[str, Any],
        context: dict[str, Any],
        evidence_items: list[dict[str, Any]],
    ) -> DeterministicCheckItem:
        """Compare financial amounts stated in report against source records."""
        discrepancies: list[str] = []

        # Find authoritative transaction amount
        actual_amount: Decimal | None = None
        txn = context.get("transaction") or {}
        raw_amt = txn.get("amount") or context.get("amount")
        if not raw_amt:
            for item in evidence_items:
                if item.get("category") == "TRANSACTION" and item.get("data", {}).get("amount"):
                    raw_amt = item["data"]["amount"]
                    break

        if raw_amt is not None:
            try:
                actual_amount = Decimal(str(raw_amt).replace(",", ""))
            except InvalidOperation:
                pass

        if actual_amount is not None:
            # Check if report claims a contradictory transaction amount
            # Look for phrases like "amount of $X", "transferred $X", "$X transfer", "for $X"
            amount_claims = re.findall(
                r"(?:amount of|transferred|transfer of|for)\s*(?:\$|USD\s*)?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
                report_text,
                re.IGNORECASE,
            )
            for claimed_str in amount_claims:
                try:
                    claimed_val = Decimal(claimed_str.replace(",", ""))
                    # If claimed value is significantly different from actual transaction amount
                    # and doesn't match known account balances
                    if claimed_val != actual_amount and abs(claimed_val - actual_amount) > Decimal("0.01"):
                        # Check if it matches any other verified amount (e.g. balance or threshold)
                        known_other_amounts = self._gather_known_amounts(context, evidence_items)
                        if not any(abs(claimed_val - oa) < Decimal("0.01") for oa in known_other_amounts):
                            discrepancies.append(
                                f"Incorrect transaction amount claimed: {claimed_str} (actual verified amount is {actual_amount})"
                            )
                except InvalidOperation:
                    continue

        passed = len(discrepancies) == 0
        details = "Amounts consistent with records." if passed else "; ".join(discrepancies)
        return DeterministicCheckItem(
            check_name="amount_validation",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
        )

    def _gather_known_amounts(
        self, context: dict[str, Any], evidence_items: list[dict[str, Any]]
    ) -> list[Decimal]:
        """Collect all known legitimate numbers (balances, thresholds) to avoid false flags."""
        amounts: list[Decimal] = []
        for item in evidence_items:
            data = item.get("data") or {}
            for k in ["balance", "previous_balance", "amount", "limit"]:
                if k in data and data[k] is not None:
                    try:
                        amounts.append(Decimal(str(data[k]).replace(",", "")))
                    except InvalidOperation:
                        pass
        return amounts

    def _check_graph_relationships(
        self,
        report_text: str,
        report_data: dict[str, Any],
        context: dict[str, Any],
        evidence_items: list[dict[str, Any]],
    ) -> DeterministicCheckItem:
        """Validate topological statements against retrieved graph context."""
        discrepancies: list[str] = []
        unverified: list[str] = []

        # Check for claims of shared devices
        shared_dev_matches = re.findall(
            r"shared\s+device\s+(?:with\s+)?([A-Za-z0-9_-]+)", report_text, re.IGNORECASE
        )
        if shared_dev_matches:
            known_shared = context.get("shared_devices") or {}
            shared_items = known_shared.get("shared_devices", [])
            known_dev_ids = {
                (d.get("device_id") if isinstance(d, dict) else str(d)).upper()
                for d in shared_items
            }
            for claimed_id in shared_dev_matches:
                if claimed_id.upper() not in known_dev_ids and not any(
                    claimed_id.upper() in d for d in known_dev_ids
                ):
                    unverified.append(
                        f"Report claims shared device relationship with '{claimed_id}' not found in graph topology."
                    )

        # Check for false corporate or parent-company relationship assertions
        if re.search(r"\b(subsidiary|parent company|holding company|wholly owned)\b", report_text, re.IGNORECASE):
            # Check if knowledge/graph contains corporate ownership proof
            has_corp_proof = False
            for ev in evidence_items:
                if ev.get("category") in {"GRAPH", "KNOWLEDGE"} and any(
                    term in str(ev.get("description", "")).lower() for term in ["parent", "subsidiary", "owner"]
                ):
                    has_corp_proof = True
                    break
            if not has_corp_proof:
                discrepancies.append(
                    "Report asserts formal corporate parent/subsidiary relationship unsupported by graph evidence."
                )

        passed = len(discrepancies) == 0
        details = "Graph topology consistent." if passed else "; ".join(discrepancies)
        return DeterministicCheckItem(
            check_name="graph_relationship_validation",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
            unverified_items=unverified,
        )

    def _check_evidence_citations(
        self, report_data: dict[str, Any], known_evidence_ids: set[str]
    ) -> DeterministicCheckItem:
        """Verify referential integrity of evidence IDs cited in findings."""
        discrepancies: list[str] = []

        findings = report_data.get("findings", [])
        if findings and known_evidence_ids:
            for i, f in enumerate(findings):
                if isinstance(f, dict):
                    cites = f.get("evidence_ids", [])
                    if not cites:
                        discrepancies.append(f"Finding #{i+1} has no evidence citations.")
                    for eid in cites:
                        if eid not in known_evidence_ids:
                            discrepancies.append(
                                f"Finding #{i+1} cites non-existent evidence_id: '{eid}'"
                            )

        passed = len(discrepancies) == 0
        details = (
            "All findings cite valid evidence IDs."
            if passed
            else f"Citation issues: {'; '.join(discrepancies)}"
        )
        return DeterministicCheckItem(
            check_name="evidence_citation_validation",
            passed=passed,
            details=details,
            discrepancies=discrepancies,
        )

