import pytest

pytestmark = pytest.mark.postgres_integration


def _seed_memory(be, profile="test-025"):
    return be._execute(
        "INSERT INTO memories (content, profile) VALUES ('x', %(p)s) RETURNING id",
        {"p": profile},
        fetch="scalar",
    )


def _seed_contradiction(be, a, b):
    be._execute(
        "INSERT INTO memory_relationships (source_id, target_id, relationship) "
        "VALUES (%(a)s, %(b)s, 'contradicts')",
        {"a": a, "b": b},
        fetch="none",
    )


def test_gap_contradictions_for_ids_surfaces_out_of_result_edges(pg_fresh_db):
    h = pg_fresh_db
    be = h.be
    h.apply_sql("sql/migrations/039_gap_contradictions_scoped.sql")
    a, b, c = _seed_memory(be), _seed_memory(be), _seed_memory(be)
    _seed_contradiction(be, a, c)  # a is in the result set, c is OUT of it
    rows = be._execute(
        "SELECT * FROM gap_contradictions_for_ids(%(p)s, %(ids)s::uuid[], 10)",
        {"p": "test-025", "ids": [str(a), str(b)]},
        fetch="all",
    )
    assert rows and rows[0]["total_count"] == 1

    # an edge fully INSIDE the result set is not an out-of-result gap
    _seed_contradiction(be, a, b)
    rows2 = be._execute(
        "SELECT * FROM gap_contradictions_for_ids(%(p)s, %(ids)s::uuid[], 10)",
        {"p": "test-025", "ids": [str(a), str(b)]},
        fetch="all",
    )
    assert rows2[0]["total_count"] == 1  # still only the a<->c out-of-result edge
