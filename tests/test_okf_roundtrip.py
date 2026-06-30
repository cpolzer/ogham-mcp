"""End-to-end round-trip test: export -> import -> verify identity preservation.

Round-trip definition (locked in v0.15 design):
  - UUID survives byte-identically
  - content survives byte-identically
  - tags survive (modulo type:X re-derivation)
  - source survives
  - metadata extension fields survive (spec §4.1 round-trip preservation)

Fields that DO NOT survive (and should not):
  - embedding (regenerated)
  - access_count, last_accessed_at (runtime state)
  - created_at may be re-stamped depending on backend behaviour
"""

from pathlib import Path


def _make_memory(id_: str, content: str, tags: list[str], metadata: dict | None = None) -> dict:
    return {
        "id": id_,
        "content": content,
        "tags": tags,
        "source": "claude-code",
        "created_at": "2026-06-17T00:00:00Z",
        "metadata": metadata or {},
    }


def test_okf_roundtrip_preserves_identity(tmp_path: Path):
    """Export then re-import a fixed set of memories; assert identity preservation."""
    from ogham.okf import export_okf_bundle, import_okf_bundle

    original = [
        _make_memory(
            "7da3c025-fa77-4f0b-9d2e-1ab84e6c3f99",
            "Use UUID PKs because Supabase recommends",
            ["type:decision", "project:ogham"],
        ),
        _make_memory(
            "d3c08af7-3f2a-4d5b-a82c-6f9e1b2d4f88",
            "Gemini batch returns nulls under load",
            ["type:gotcha"],
            metadata={"language": "en"},
        ),
        _make_memory(
            "2bf662d8-1869-48e1-bd9e-1e0eaae162af",
            "Generic memory with no type",
            ["project:ogham"],
        ),
    ]
    bundle_dir = tmp_path / "rt-bundle"
    manifest = {
        "producer": "ogham-mcp/test",
        "exported_at": "2026-06-17T00:00:00Z",
        "profile": "test",
    }

    export_okf_bundle(original, bundle_dir, manifest)
    imported, stats = import_okf_bundle(bundle_dir)

    assert stats["total"] == 3
    assert stats["missing_id_count"] == 0

    # Index by id for comparison
    imported_by_id = {m["id"]: m for m in imported}
    for orig in original:
        rt = imported_by_id[orig["id"]]
        assert rt["content"] == orig["content"], f"content drift for {orig['id']}"
        assert rt["source"] == orig["source"]
        # Tags: original type:X tags should be preserved (winner becomes OKF type
        # and is re-derived to tag on import; losers stay as tags throughout)
        assert sorted(rt["tags"]) == sorted(orig["tags"]), f"tag drift for {orig['id']}"
        # Metadata extension fields preserved per spec §4.1
        for k, v in orig["metadata"].items():
            assert rt["metadata"].get(k) == v, f"metadata drift for {orig['id']} key {k}"


def test_okf_roundtrip_handles_default_type_memory(tmp_path: Path):
    """A memory with no type:X tag round-trips as type=Memory and tag-namespace
    is NOT polluted by an injected `type:memory` tag.
    """
    from ogham.okf import export_okf_bundle, import_okf_bundle

    original = [_make_memory("11111111-2222-3333-4444-555555555555", "no type tag", ["project:x"])]
    bundle_dir = tmp_path / "rt-default"
    export_okf_bundle(original, bundle_dir, {"producer": "p", "exported_at": "t", "profile": "p"})
    imported, _ = import_okf_bundle(bundle_dir)
    assert imported[0]["tags"] == ["project:x"]
    assert "type:memory" not in imported[0]["tags"]


def test_okf_roundtrip_index_md_declares_okf_version(tmp_path: Path):
    """Exported bundle is conformant: index.md declares okf_version: 0.1."""
    import yaml

    from ogham.okf import export_okf_bundle

    export_okf_bundle(
        [_make_memory("11111111-2222-3333-4444-555555555555", "x", [])],
        tmp_path,
        {"producer": "p", "exported_at": "t", "profile": "p"},
    )
    index_text = (tmp_path / "index.md").read_text(encoding="utf-8")
    yaml_block = index_text.split("---\n", 2)[1]
    parsed = yaml.safe_load(yaml_block)
    assert parsed["okf_version"] == "0.1"
