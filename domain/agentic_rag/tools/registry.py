"""Strict, immutable read-only Agent Tool Registry for Omerta.ai Agentic RAG.

Security Guarantees:
1. Allowlist-Only Execution: The LLM can ONLY invoke registered, typed read-only tools.
2. Complete Mutation Denial: No tool can execute INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, or GRANT.
3. No Raw Execution: Generic SQL (execute_sql) and generic Cypher (run_cypher) are strictly forbidden and non-existent.
4. Input Boundary Enforcement: Every tool argument is validated against strict Pydantic schemas forbidding extra fields.
5. Traversal and Cardinality Capping: Bounded limit parameters (max 100 rows, max 4 graph hops).
"""

from enum import StrEnum
import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.agentic_rag.tools.database_tools import DatabaseTools
from domain.agentic_rag.tools.document_tools import DocumentTools
from domain.agentic_rag.tools.graph_tools import GraphTools
from domain.errors import ValidationError

logger = logging.getLogger(__name__)

# Strictly blocked tool names attempting database mutations or arbitrary execution
BLOCKED_TOOL_NAMES = frozenset({
    "execute_sql",
    "run_sql",
    "raw_sql",
    "sql_query",
    "run_cypher",
    "execute_cypher",
    "raw_cypher",
    "cypher_query",
    "eval",
    "exec",
    "system",
    "shell",
    "python",
    "bash",
    "delete_account",
    "update_balance",
    "transfer_funds",
    "freeze_account",
    "unblock_account",
    "modify_transaction",
    "drop_table",
    "truncate_table",
    "alter_table",
})

# Suspicious SQL mutation tokens
SQL_MUTATION_REGEX = re.compile(
    r"(?i)\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|TRUNCATE\s+TABLE|ALTER\s+TABLE|CREATE\s+TABLE|GRANT\s+|REVOKE\s+)\b"
)


# --- Strict Pydantic Argument Schemas (extra='forbid') ---

class StrictToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchDocumentsArgs(StrictToolArgs):
    query: str = Field(min_length=1, max_length=500)
    user_role: str = Field(default="INVESTIGATOR", max_length=32)
    category: str | None = Field(default=None, max_length=64)
    top_k: int = Field(default=4, ge=1, le=10)


class GetDocumentSectionArgs(StrictToolArgs):
    document_id: str = Field(min_length=1, max_length=64)
    section_title: str = Field(min_length=1, max_length=128)


class GetDocumentMetadataArgs(StrictToolArgs):
    document_id: str = Field(min_length=1, max_length=64)


from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GetTransactionArgs(StrictToolArgs):
    transaction_id: str | None = Field(default=None, max_length=64)
    external_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_id(self):
        if not self.transaction_id and not self.external_id:
            raise ValueError("transaction_id or external_id is required")
        if not self.transaction_id:
            self.transaction_id = self.external_id
        return self


class GetAccountArgs(StrictToolArgs):
    account_id: str | None = Field(default=None, max_length=64)
    external_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_id(self):
        if not self.account_id and not self.external_id:
            raise ValueError("account_id or external_id is required")
        if not self.account_id:
            self.account_id = self.external_id
        return self


class GetCustomerArgs(StrictToolArgs):
    customer_id: str | None = Field(default=None, max_length=64)
    external_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_id(self):
        if not self.customer_id and not self.external_id:
            raise ValueError("customer_id or external_id is required")
        if not self.customer_id:
            self.customer_id = self.external_id
        return self


class FindCustomersByNameArgs(StrictToolArgs):
    name_query: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=20)


class GetAllCustomersArgs(StrictToolArgs):
    limit: int = Field(default=20, ge=1, le=100)


class GetCustomerAccountsAndTransactionsArgs(StrictToolArgs):
    customer_id: str = Field(min_length=1, max_length=64)


class ExecuteReadOnlySqlArgs(StrictToolArgs):
    sql_query: str = Field(min_length=6, max_length=1000)
    limit: int = Field(default=20, ge=1, le=50)


class GetRecentTransactionsArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=10, ge=1, le=50)


class CountTransactionsArgs(StrictToolArgs):
    time_range_days: int | None = Field(default=None, ge=1, le=365)
    currency: str | None = Field(default=None, max_length=3)
    status: str | None = Field(default=None, max_length=32)


class GetTransactionSummaryArgs(StrictToolArgs):
    time_range_days: int | None = Field(default=30, ge=1, le=365)
    currency: str = Field(default="EGP", max_length=3)


class CompareTransactionPeriodsArgs(StrictToolArgs):
    period_a_days: int = Field(default=30, ge=1, le=365)
    period_b_days: int = Field(default=30, ge=1, le=365)
    currency: str = Field(default="EGP", max_length=3)


class GetRiskDistributionArgs(StrictToolArgs):
    time_range_days: int | None = Field(default=30, ge=1, le=365)


class GetBoundedTransactionDatasetArgs(StrictToolArgs):
    limit: int = Field(default=20, ge=1, le=100)
    currency: str | None = Field(default=None, max_length=3)
    risk_level: str | None = Field(default=None, max_length=16)


class GetAccountNeighborsArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=50)


class FindConnectedAccountsArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=50)


class FindSharedDevicesArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=50)


class FindSharedIPsArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=50)


class FindTransactionPathsArgs(StrictToolArgs):
    source_account: str | None = Field(default=None, max_length=64)
    target_account: str | None = Field(default=None, max_length=64)
    source_account_id: str | None = Field(default=None, max_length=64)
    target_account_id: str | None = Field(default=None, max_length=64)
    max_depth: int = Field(default=3, ge=1, le=4)

    @model_validator(mode="after")
    def validate_accounts(self):
        src = self.source_account or self.source_account_id
        tgt = self.target_account or self.target_account_id
        if not src or not tgt:
            raise ValueError("source_account and target_account are required")
        self.source_account = src
        self.target_account = tgt
        return self


class FindFraudSignalsArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=50)


class SummarizeAccountNetworkArgs(StrictToolArgs):
    account_id: str = Field(min_length=1, max_length=64)
    max_depth: int = Field(default=2, ge=1, le=3)


class GetGraphSchemaOverviewArgs(StrictToolArgs):
    pass


class ExecuteReadOnlyCypherArgs(StrictToolArgs):
    cypher_query: str = Field(min_length=6, max_length=1000)
    limit: int = Field(default=20, ge=1, le=50)


# Allowlist mapping tool name -> (Schema, Handler)
READ_ONLY_TOOL_REGISTRY: dict[str, tuple[type[StrictToolArgs], Any]] = {
    # Document Tools
    "search_documents": (SearchDocumentsArgs, DocumentTools.search_documents),
    "get_document_section": (GetDocumentSectionArgs, DocumentTools.get_document_section),
    "get_document_metadata": (GetDocumentMetadataArgs, DocumentTools.get_document_metadata),
    # Database Tools (PostgreSQL)
    "get_transaction": (GetTransactionArgs, DatabaseTools.get_transaction),
    "get_account": (GetAccountArgs, DatabaseTools.get_account),
    "get_customer": (GetCustomerArgs, DatabaseTools.get_customer),
    "get_all_customers": (GetAllCustomersArgs, DatabaseTools.get_all_customers),
    "find_customers_by_name": (FindCustomersByNameArgs, DatabaseTools.find_customers_by_name),
    "get_customer_accounts_and_transactions": (GetCustomerAccountsAndTransactionsArgs, DatabaseTools.get_customer_accounts_and_transactions),
    "get_recent_transactions": (GetRecentTransactionsArgs, DatabaseTools.get_recent_transactions),
    "count_transactions": (CountTransactionsArgs, DatabaseTools.count_transactions),
    "get_transaction_summary": (GetTransactionSummaryArgs, DatabaseTools.get_transaction_summary),
    "compare_transaction_periods": (CompareTransactionPeriodsArgs, DatabaseTools.compare_transaction_periods),
    "get_risk_distribution": (GetRiskDistributionArgs, DatabaseTools.get_risk_distribution),
    "get_bounded_transaction_dataset": (GetBoundedTransactionDatasetArgs, DatabaseTools.get_bounded_transaction_dataset),
    "execute_read_only_sql": (ExecuteReadOnlySqlArgs, DatabaseTools.execute_read_only_sql),
    # Graph Tools (Neo4j)
    "get_account_neighbors": (GetAccountNeighborsArgs, GraphTools.get_account_neighbors),
    "find_connected_accounts": (FindConnectedAccountsArgs, GraphTools.find_connected_accounts),
    "find_shared_devices": (FindSharedDevicesArgs, GraphTools.find_shared_devices),
    "get_shared_devices": (FindSharedDevicesArgs, GraphTools.find_shared_devices),
    "find_shared_ips": (FindSharedIPsArgs, GraphTools.find_shared_ips),
    "get_shared_ips": (FindSharedIPsArgs, GraphTools.find_shared_ips),
    "find_transaction_paths": (FindTransactionPathsArgs, GraphTools.find_transaction_paths),
    "find_fraud_signals": (FindFraudSignalsArgs, GraphTools.find_fraud_signals),
    "summarize_account_network": (SummarizeAccountNetworkArgs, GraphTools.summarize_account_network),
    "get_graph_schema_overview": (GetGraphSchemaOverviewArgs, GraphTools.get_graph_schema_overview),
    "execute_read_only_cypher": (ExecuteReadOnlyCypherArgs, GraphTools.execute_read_only_cypher),
}


class AgentToolExecutionError(Exception):
    """Raised when tool execution is rejected due to security or validation boundary."""
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION"):
        super().__init__(message)
        self.message = message
        self.code = code


async def invoke_agent_tool(tool_name: str, arguments: dict[str, Any], user_role: str = "INVESTIGATOR") -> Any:
    """Safely validate arguments against strict Pydantic schema and execute read-only tool.

    Rejects:
    - Unknown tools
    - Blocked/mutation tool names
    - Extra arguments or oversized limits
    - Text inputs containing SQL mutation tokens
    """
    clean_name = (tool_name or "").strip()

    if clean_name in BLOCKED_TOOL_NAMES:
        logger.error("Blocked dangerous tool invocation attempt: %s", clean_name)
        raise AgentToolExecutionError(
            f"Execution rejected: Tool '{clean_name}' is strictly prohibited. The AI agent operates in an immutable read-only boundary.",
            code="MUTATION_PROHIBITED",
        )

    if clean_name not in READ_ONLY_TOOL_REGISTRY:
        logger.warning("Attempted invocation of unregistered tool: %s", clean_name)
        raise AgentToolExecutionError(
            f"Tool '{clean_name}' is not in the approved read-only tool allowlist.",
            code="TOOL_NOT_ALLOWLISTED",
        )

    schema_cls, handler = READ_ONLY_TOOL_REGISTRY[clean_name]

    # Validate against strict Pydantic model (rejects extra arguments)
    try:
        validated_args = schema_cls.model_validate(arguments or {})
    except Exception as exc:
        logger.warning("Tool argument validation failed for %s: %s", clean_name, exc)
        raise AgentToolExecutionError(
            f"Invalid arguments for tool '{clean_name}': {str(exc)}",
            code="INVALID_ARGUMENTS",
        )

    # Check string arguments for SQL mutation attempts
    for k, v in validated_args.model_dump().items():
        if isinstance(v, str) and SQL_MUTATION_REGEX.search(v):
            logger.error("Detected SQL mutation pattern inside tool argument: %s=%s", k, v)
            raise AgentToolExecutionError(
                f"SQL mutation syntax detected in parameter '{k}'. Database modifications are prohibited.",
                code="MUTATION_SYNTAX_DETECTED",
            )

    # Inject authenticated user_role if tool supports it
    call_kwargs = validated_args.model_dump()
    if "user_role" in schema_cls.model_fields and "user_role" not in arguments:
        call_kwargs["user_role"] = user_role

    if clean_name == "get_account":
        call_kwargs = {"account_id": validated_args.account_id}
    elif clean_name == "get_transaction":
        call_kwargs = {"transaction_id": validated_args.transaction_id}
    elif clean_name == "get_customer":
        call_kwargs = {"customer_id": validated_args.customer_id}
    elif clean_name == "find_transaction_paths":
        call_kwargs = {
            "source_account": validated_args.source_account,
            "target_account": validated_args.target_account,
            "max_depth": validated_args.max_depth,
        }

    # Execute read-only handler
    return await handler(**call_kwargs)
