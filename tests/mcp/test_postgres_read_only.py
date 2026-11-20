"""Integration tests for PostgreSQL Read-Only Role Isolation (omerta_mcp_reader).

Verifies that:
1. MCP database connections authenticate as 'omerta_mcp_reader'.
2. omerta_mcp_reader is NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION.
3. SELECT succeeds across schema tables.
4. INSERT fails with InsufficientPrivilegeError / permission denied.
5. UPDATE fails with InsufficientPrivilegeError / permission denied.
6. DELETE fails with InsufficientPrivilegeError / permission denied.
7. TRUNCATE fails with InsufficientPrivilegeError / permission denied.
8. DDL (CREATE, DROP) fails with InsufficientPrivilegeError / permission denied.
9. MCP servers are bound to get_mcp_engine() rather than superuser get_engine().
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import create_mcp_engine, get_engine, get_mcp_engine
import mcp_servers.transaction_server.tools as txn_tools
import mcp_servers.risk_server.tools as risk_tools
import mcp_servers.knowledge_server.tools as knowledge_tools


@pytest.fixture
async def mcp_db_session():
    """Per-test fresh AsyncSession backed by a NullPool read-only engine."""
    engine = create_mcp_engine(use_null_pool=True)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_mcp_engine_identity_and_privileges(mcp_db_session):
    """Verify runtime user identity and non-superuser status."""
    mcp_engine = get_mcp_engine()
    assert mcp_engine.url.username == "omerta_mcp_reader"
    assert get_engine().url.username == "omerta"

    result = await mcp_db_session.execute(text("SELECT current_user, session_user;"))
    current_user, session_user = result.first()
    assert current_user == "omerta_mcp_reader"
    assert session_user == "omerta_mcp_reader"

    # Check role flags in pg_roles
    role_result = await mcp_db_session.execute(
        text("SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication FROM pg_roles WHERE rolname = current_user;")
    )
    rolsuper, rolcreaterole, rolcreatedb, rolreplication = role_result.first()
    assert rolsuper is False, "MCP reader must NOT be a superuser"
    assert rolcreaterole is False, "MCP reader must NOT have createrole privileges"
    assert rolcreatedb is False, "MCP reader must NOT have createdb privileges"
    assert rolreplication is False, "MCP reader must NOT have replication privileges"


@pytest.mark.asyncio
async def test_mcp_select_succeeds(mcp_db_session):
    """Verify SELECT access is permitted on public schema tables."""
    # Schema metadata SELECT
    res = await mcp_db_session.execute(
        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    )
    count = res.scalar()
    assert count > 0

    # Query existing table
    txn_res = await mcp_db_session.execute(text("SELECT COUNT(*) FROM transactions;"))
    assert txn_res.scalar() >= 0


@pytest.mark.asyncio
async def test_mcp_insert_fails(mcp_db_session):
    """Verify INSERT is physically rejected by PostgreSQL."""
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("INSERT INTO transactions (id) VALUES (999999999);"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )


@pytest.mark.asyncio
async def test_mcp_update_fails(mcp_db_session):
    """Verify UPDATE is physically rejected by PostgreSQL."""
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("UPDATE accounts SET balance = 0 WHERE id = 999999999;"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )


@pytest.mark.asyncio
async def test_mcp_delete_fails(mcp_db_session):
    """Verify DELETE is physically rejected by PostgreSQL."""
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("DELETE FROM accounts WHERE id = 999999999;"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )


@pytest.mark.asyncio
async def test_mcp_truncate_fails(mcp_db_session):
    """Verify TRUNCATE is physically rejected by PostgreSQL."""
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("TRUNCATE TABLE transactions;"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )


@pytest.mark.asyncio
async def test_mcp_ddl_fails(mcp_db_session):
    """Verify DDL operations (CREATE, DROP) are physically rejected by PostgreSQL."""
    # Test CREATE TABLE failure
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("CREATE TABLE test_mcp_forbidden (id int);"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )

    # Rollback aborted transaction before testing DROP TABLE
    await mcp_db_session.rollback()

    # Test DROP TABLE failure
    with pytest.raises((DBAPIError, ProgrammingError)) as exc_info:
        await mcp_db_session.execute(text("DROP TABLE transactions;"))
        await mcp_db_session.flush()
    err_msg = str(exc_info.value).lower()
    assert (
        "permission denied" in err_msg
        or "must be owner" in err_msg
        or "insufficientprivilegeerror" in err_msg
    )


def test_mcp_servers_use_isolated_read_only_engine():
    """Verify that all database-backed MCP servers use get_mcp_engine instead of get_engine."""
    import inspect

    for mod, name in [
        (txn_tools, "Transaction Server"),
        (risk_tools, "Risk Server"),
        (knowledge_tools, "Knowledge Server"),
    ]:
        source = inspect.getsource(mod._execute)
        assert "get_mcp_engine()" in source, f"{name} _execute must use get_mcp_engine()"
        assert "get_engine()" not in source, f"{name} _execute must NOT use get_engine()"
