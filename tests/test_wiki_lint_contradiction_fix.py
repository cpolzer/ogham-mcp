"""Migration 040: wiki_lint_contradictions both-endpoint profile filter (#262).

The legacy function (migration 031) joined only the SOURCE endpoint to
``memories`` and filtered ``m.profile = p_profile`` on that side alone. A
within-profile contradiction means BOTH memories live in the profile, so the
correct filter joins and filters both endpoints (mirroring migration 039's
``gap_contradictions_for_ids``). These live-DB tests prove the corrected
scoping. Scratch DB on port 5433; see plan 2026-05-27-gap-analysis-v1 Task 10.
"""

import pytest

pytestmark = pytest.mark.postgres_integration


def _seed_memory(be, profile="test-025"):
    return be._execute(
        "INSERT INTO memories (content, profile) VALUES ('x', %(p)s) RETURNING id",
        {"p": profile},
        fetch="scalar",
    )


def _seed_contradiction(be, a, b):
    # memory_relationships.id is a bigint sequence -- omit it, let it assign.
    be._execute(
        "INSERT INTO memory_relationships (source_id, target_id, relationship) "
        "VALUES (%(a)s, %(b)s, 'contradicts')",
        {"a": a, "b": b},
        fetch="none",
    )


def test_lint_contradiction_counts_in_profile_edge(pg_fresh_db):
    """Smoke: after the 040 rewrite a contradiction with both endpoints in the
    profile is still counted (the common, realistic case must be unchanged)."""
    h = pg_fresh_db
    be = h.be
    h.apply_sql("sql/migrations/040_fix_lint_contradiction_filter.sql")
    a, b = _seed_memory(be), _seed_memory(be)
    _seed_contradiction(be, a, b)

    from ogham.wiki_lint import find_contradictions

    assert find_contradictions("test-025")["count"] == 1


def test_lint_contradiction_requires_both_endpoints_in_profile(pg_fresh_db):
    """The fix. The legacy filter was source-side-only, so a cross-profile edge
    whose source happened to sit in the profile was counted even though the
    contradiction is not within-profile. Migration 040 joins and filters BOTH
    endpoints, so that edge is excluded. The source-only legacy function would
    return 2 here (both edges have source ``a`` in profile); the fix returns 1.
    """
    h = pg_fresh_db
    be = h.be
    h.apply_sql("sql/migrations/040_fix_lint_contradiction_filter.sql")
    a, b = _seed_memory(be, "test-025"), _seed_memory(be, "test-025")
    foreign = _seed_memory(be, "test-025-foreign")
    _seed_contradiction(be, a, b)  # both in profile -> counted
    _seed_contradiction(be, a, foreign)  # target out of profile -> excluded by fix
    try:
        from ogham.wiki_lint import find_contradictions

        assert find_contradictions("test-025")["count"] == 1
    finally:
        # The pg_fresh_db harness only cleans the test-025 profile. Deleting a's
        # row cascades the (a, foreign) edge away, but the foreign memory itself
        # persists -- tidy it so the shared scratch DB stays clean.
        be._execute(
            "DELETE FROM memories WHERE profile = %(p)s",
            {"p": "test-025-foreign"},
            fetch="none",
        )
