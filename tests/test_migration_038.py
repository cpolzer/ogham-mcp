"""Migration 038 + Data API grants integration tests.

Verifies (a) 038 forward applies cleanly on vanilla Postgres (no
service_role) and Supabase-style Postgres (service_role present);
(b) on Supabase-style installs the 9 Ogham tables get SELECT/INSERT/
UPDATE/DELETE granted to service_role; (c) the rollback revokes
those grants cleanly; (d) the migration is idempotent.

Surfaced 2026-04-28: Supabase announced that tables in `public` will
no longer be auto-exposed to the Data API by 2026-05-30 (new projects)
and 2026-10-30 (all projects). Migration 038 adds explicit GRANTs so
Ogham's PostgREST access path keeps working.
Source: https://github.com/orgs/supabase/discussions/45329
"""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent / "sql/migrations"
MIG_025 = MIGRATIONS_DIR / "025_memory_lifecycle.sql"
MIG_026 = MIGRATIONS_DIR / "026_memory_lifecycle_split.sql"
MIG_028 = MIGRATIONS_DIR / "028_topic_summaries.sql"
MIG_036 = MIGRATIONS_DIR / "036_entities_backfill.sql"
MIG_038 = MIGRATIONS_DIR / "038_data_api_grants.sql"
ROLLBACK_038 = (
    Path(__file__).parent.parent / "sql/migrations/rollback/DANGER_038_data_api_grants.sql"
)

OGHAM_TABLES = [
    "memories",
    "profile_settings",
    "memory_lifecycle",
    "memory_relationships",
    "audit_log",
    "entities",
    "memory_entities",
    "topic_summaries",
    "topic_summary_sources",
]
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")


def _can_connect() -> bool:
    try:
        from ogham.config import settings

        if settings.database_backend != "postgres":
            return False
        from ogham.backends.postgres import PostgresBackend

        backend = PostgresBackend()
        backend._execute("SELECT 1", fetch="scalar")
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.postgres_integration,
    pytest.mark.skipif(
        not _can_connect(),
        reason="Postgres backend not configured or unreachable",
    ),
]


def _service_role_exists(backend) -> bool:
    return bool(
        backend._execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'service_role'",
            fetch="scalar",
        )
    )


def _can_create_role(backend) -> bool:
    """Probe whether the test connection role can CREATE ROLE.

    CREATE ROLE requires CREATEROLE attribute or superuser; on
    constrained CI runners we want to skip the role-present tests
    rather than fail them.
    """
    try:
        backend._execute("CREATE ROLE _ogham_role_probe_038 NOLOGIN", fetch="none")
        backend._execute("DROP ROLE _ogham_role_probe_038", fetch="none")
        return True
    except Exception:
        return False


def _privileges_for(backend, role: str) -> set[tuple[str, str]]:
    rows = backend._execute(
        "SELECT table_name, privilege_type "
        "  FROM information_schema.table_privileges "
        " WHERE table_schema = 'public' "
        "   AND grantee = %(role)s "
        "   AND table_name = ANY(%(tables)s)",
        {"role": role, "tables": OGHAM_TABLES},
        fetch="all",
    )
    return {(r["table_name"], r["privilege_type"]) for r in rows or []}


def _apply_baseline(pg_fresh_db):
    """Bring the scratch DB to the state migration 038 grants on: all 9
    Ogham tables present.

    The autouse session fixture loads schema_postgres.sql (memories,
    profile_settings, memory_relationships, audit_log, entities,
    memory_entities) and applies 025+026 once. But the pg_fresh_db
    teardown drops memory_lifecycle, entities, memory_entities and the
    memories.stage column, so by the time 038's tests run after any other
    pg_fresh_db test in the session those four GRANT targets are gone and
    a 038 GRANT raises UndefinedTable. Re-apply the migrations that create
    them. All four are idempotent (IF NOT EXISTS / CREATE OR REPLACE), so
    re-running on an intact DB is a no-op.
    """
    pg_fresh_db.apply_sql(MIG_025)  # memories.stage + profile_settings decay cols
    pg_fresh_db.apply_sql(MIG_026)  # memory_lifecycle table + triggers
    pg_fresh_db.apply_sql(MIG_036)  # entities + memory_entities
    pg_fresh_db.apply_sql(MIG_028)  # topic_summaries + topic_summary_sources


def test_038_applies_cleanly_without_service_role(pg_fresh_db):
    """Forward migration must no-op without error when service_role is
    absent (Neon, self-hosted PG, smoke-test DB).
    """
    from ogham.backends.postgres import PostgresBackend

    backend = PostgresBackend()
    if _service_role_exists(backend):
        pytest.skip("service_role exists on this DB; can't test no-op path")

    _apply_baseline(pg_fresh_db)
    pg_fresh_db.apply_sql(MIG_038)  # must not raise

    assert _privileges_for(backend, "service_role") == set()


def test_038_grants_service_role_when_role_exists(pg_fresh_db):
    """When service_role exists, the 9 Ogham tables get all four DML
    privileges granted.
    """
    from ogham.backends.postgres import PostgresBackend

    backend = PostgresBackend()
    if not _can_create_role(backend):
        pytest.skip("Test connection role cannot CREATE ROLE")
    if _service_role_exists(backend):
        pytest.skip("service_role already exists; can't isolate test")

    _apply_baseline(pg_fresh_db)
    backend._execute("CREATE ROLE service_role NOLOGIN", fetch="none")
    try:
        pg_fresh_db.apply_sql(MIG_038)
        grants = _privileges_for(backend, "service_role")
        expected = {(t, p) for t in OGHAM_TABLES for p in PRIVILEGES}
        assert grants == expected, f"missing={expected - grants!r} extra={grants - expected!r}"
    finally:
        pg_fresh_db.apply_rollback(ROLLBACK_038)
        backend._execute("DROP ROLE IF EXISTS service_role", fetch="none")


def test_038_rollback_revokes_grants(pg_fresh_db):
    """The rollback must remove the GRANTs that 038 added."""
    from ogham.backends.postgres import PostgresBackend

    backend = PostgresBackend()
    if not _can_create_role(backend):
        pytest.skip("Test connection role cannot CREATE ROLE")
    if _service_role_exists(backend):
        pytest.skip("service_role already exists; can't isolate test")

    _apply_baseline(pg_fresh_db)
    backend._execute("CREATE ROLE service_role NOLOGIN", fetch="none")
    try:
        pg_fresh_db.apply_sql(MIG_038)
        assert _privileges_for(backend, "service_role"), "precondition: grants present"

        pg_fresh_db.apply_rollback(ROLLBACK_038)
        assert _privileges_for(backend, "service_role") == set()
    finally:
        backend._execute("DROP ROLE IF EXISTS service_role", fetch="none")


def test_038_is_idempotent(pg_fresh_db):
    """Re-running 038 must not error. GRANT on an existing grant is a
    no-op in PostgreSQL; the DO block guard handles repeated runs.
    """
    _apply_baseline(pg_fresh_db)
    pg_fresh_db.apply_sql(MIG_038)
    pg_fresh_db.apply_sql(MIG_038)  # must not raise


def test_038_does_not_grant_anon_or_authenticated(pg_fresh_db):
    """Defense-in-depth: 038 grants only to service_role. anon is
    denied at RLS + locked out of RPC EXECUTE in migration 037;
    authenticated is currently unused by Ogham.
    """
    from ogham.backends.postgres import PostgresBackend

    backend = PostgresBackend()
    if not _can_create_role(backend):
        pytest.skip("Test connection role cannot CREATE ROLE")
    if _service_role_exists(backend):
        pytest.skip("service_role already exists; can't isolate test")

    # Create all three Supabase-style roles to make the assertion meaningful.
    _apply_baseline(pg_fresh_db)
    for role in ("anon", "authenticated", "service_role"):
        if not backend._execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %(r)s",
            {"r": role},
            fetch="scalar",
        ):
            backend._execute(f"CREATE ROLE {role} NOLOGIN", fetch="none")
    try:
        pg_fresh_db.apply_sql(MIG_038)
        assert _privileges_for(backend, "service_role"), "service_role got grants"
        assert _privileges_for(backend, "anon") == set(), "anon must not be granted"
        assert _privileges_for(backend, "authenticated") == set(), (
            "authenticated must not be granted"
        )
    finally:
        pg_fresh_db.apply_rollback(ROLLBACK_038)
        for role in ("anon", "authenticated", "service_role"):
            backend._execute(f"DROP ROLE IF EXISTS {role}", fetch="none")
