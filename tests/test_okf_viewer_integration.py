from pathlib import Path
from uuid import uuid4

from ogham.okf.bundle import export_okf_bundle


def _mem(content: str, tags: list[str] | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "content": content,
        "tags": tags or [],
        "metadata": {},
        "source": "claude-code",
        "created_at": "2026-06-18T10:00:00+00:00",
        "updated_at": "2026-06-18T10:00:00+00:00",
    }


def test_export_okf_bundle_no_viewer_by_default(tmp_path: Path) -> None:
    bundle = tmp_path / "b"
    export_okf_bundle([_mem("hello")], bundle, manifest={"producer": "test"})
    assert not (bundle / "viewer.html").exists()


def test_export_okf_bundle_include_viewer_writes_html(tmp_path: Path) -> None:
    bundle = tmp_path / "b"
    export_okf_bundle(
        [_mem("hello world", ["type:decision"])],
        bundle,
        manifest={"producer": "test"},
        include_viewer=True,
    )
    viewer = bundle / "viewer.html"
    assert viewer.exists()
    html = viewer.read_text()
    assert "Cytoscape Consortium" in html
    assert "hello world" in html


from unittest.mock import patch  # noqa: E402


def test_export_memories_okf_default_includes_viewer(tmp_path, monkeypatch):
    from ogham import export_import

    monkeypatch.chdir(tmp_path)
    with patch.object(export_import, "_list_all_memories", return_value=[_mem("x")]):
        result_path = Path(export_import.export_memories("default", format="okf"))
    assert (result_path / "viewer.html").exists()


def test_export_memories_okf_opt_out(tmp_path, monkeypatch):
    from ogham import export_import

    monkeypatch.chdir(tmp_path)
    with patch.object(export_import, "_list_all_memories", return_value=[_mem("x")]):
        result_path = Path(
            export_import.export_memories("default", format="okf", include_viewer=False)
        )
    assert not (result_path / "viewer.html").exists()
