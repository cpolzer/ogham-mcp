"""Tests for export_profile(format='okf') tool integration."""

from pathlib import Path

import pytest


@pytest.fixture
def fake_memories(monkeypatch):
    """Stub _list_all_memories() so the test doesn't need a real DB."""
    memories = [
        {
            "id": "7da3c025-fa77-4f0b-9d2e-1ab84e6c3f99",
            "content": "Use UUID PKs",
            "tags": ["type:decision", "project:ogham"],
            "source": "claude-code",
            "created_at": "2026-06-17T00:00:00Z",
            "metadata": {},
            "profile": "test_profile",
        },
    ]
    from ogham import export_import

    monkeypatch.setattr(export_import, "_list_all_memories", lambda profile: memories)
    return memories


def test_export_profile_okf_format_returns_bundle_path(fake_memories, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from ogham.tools.memory import export_profile

    # OKF format returns a bundle path string instead of an inline JSON/markdown blob
    result = export_profile(format="okf")
    assert result["status"] == "exported"
    assert result["format"] == "okf"
    bundle_path = Path(result["data"])
    assert bundle_path.exists()
    assert (bundle_path / "index.md").exists()
    assert (bundle_path / "memories").is_dir()


def test_export_profile_okf_writes_one_file_per_memory(fake_memories, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from ogham.tools.memory import export_profile

    result = export_profile(format="okf")
    bundle_path = Path(result["data"])
    files = list((bundle_path / "memories").glob("*.md"))
    assert len(files) == 1
    assert "use-uuid-pks-7da3c025.md" in files[0].name


def test_export_profile_rejects_unknown_format():
    from ogham.tools.memory import export_profile

    with pytest.raises(ValueError, match="format must be"):
        export_profile(format="xml")
