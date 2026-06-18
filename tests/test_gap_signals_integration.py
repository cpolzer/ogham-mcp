import pytest

pytestmark = pytest.mark.postgres_integration


def _seed_memory(be, profile="test-025"):
    return be._execute(
        "INSERT INTO memories (content, profile) VALUES ('x', %(p)s) RETURNING id",
        {"p": profile},
        fetch="scalar",
    )


def _seed_contradiction(be, a, b):
    # memory_relationships.id is a bigint sequence -- omit it, let the sequence assign.
    be._execute(
        "INSERT INTO memory_relationships (source_id, target_id, relationship) "
        "VALUES (%(a)s, %(b)s, 'contradicts')",
        {"a": a, "b": b},
        fetch="none",
    )


def test_backend_scoped_contradictions(pg_fresh_db):
    h = pg_fresh_db
    be = h.be
    h.apply_sql("sql/migrations/039_gap_contradictions_scoped.sql")
    a, _b, c = _seed_memory(be), _seed_memory(be), _seed_memory(be)
    _seed_contradiction(be, a, c)  # c is out of the [a] result set

    from ogham.database import gap_out_of_result_contradictions

    res = gap_out_of_result_contradictions("test-025", [str(a)], sample_size=10)
    assert res["count"] == 1
    assert res["pairs"]  # non-empty


def test_end_to_end_deep_surfaces_out_of_result(pg_fresh_db, monkeypatch):
    """Full path: hybrid_search(gap="deep") attaches a gap_note whose only
    material signal is a contradiction with a memory that did NOT rank.

    Seed a<->c as 'contradicts'. Force the result set to [a, b] (both healthy:
    recent + high confidence); c is out of the result set, so its contradiction
    is invisible to in-result signals and surfaces only via the deep lookup."""
    h = pg_fresh_db
    be = h.be
    h.apply_sql("sql/migrations/039_gap_contradictions_scoped.sql")
    a, b, c = _seed_memory(be), _seed_memory(be), _seed_memory(be)
    _seed_contradiction(be, a, c)  # c is OUT of the [a, b] result set below

    import ogham.service as service
    import ogham.tools.memory as memtool
    from ogham import flow_control

    recent = "2026-05-26T00:00:00+00:00"
    rows = [
        {"id": str(a), "created_at": recent, "confidence": 0.9, "tags": []},
        {"id": str(b), "created_at": recent, "confidence": 0.9, "tags": []},
    ]
    monkeypatch.setattr(service, "search_memories_enriched", lambda **k: rows)
    monkeypatch.setattr(memtool, "get_active_profile", lambda: "test-025")
    monkeypatch.setattr(flow_control, "recall_enabled", lambda: True)
    monkeypatch.setattr(memtool.settings, "wiki_injection_enabled", False, raising=False)

    out = memtool.hybrid_search("q", gap="deep")

    assert out["gap_note"] is not None
    # In-result signals are healthy; the out-of-result edge is the material one.
    assert out["gap_note"]["contradictions"]["count"] == 1
