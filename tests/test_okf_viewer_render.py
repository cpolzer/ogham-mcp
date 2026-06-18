import json
import re
from pathlib import Path

import pytest

from ogham.okf.viewer import build_viewer, load_asset, render_html


def test_load_asset_returns_cytoscape_text() -> None:
    text = load_asset("cytoscape.min.js")
    assert text.startswith("/**")
    assert "Cytoscape Consortium" in text
    assert len(text) > 100_000


def test_load_asset_returns_css() -> None:
    text = load_asset("viewer.css")
    assert "--gold" in text
    assert "#D4A843" in text


def test_load_asset_returns_js() -> None:
    text = load_asset("viewer.js")
    assert "cytoscape(" in text
    assert "__OKF_ELEMENTS__" in text


def test_load_asset_unknown_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_asset("nope.txt")


def test_render_html_inlines_all_assets() -> None:
    html = render_html(
        [
            {
                "data": {
                    "id": "a",
                    "label": "Alpha",
                    "type": "Memory",
                    "tags": [],
                    "color": "#4ADE80",
                    "size": 30,
                }
            }
        ],
        "demo",
    )
    # No external asset references (script src= or link href=)
    assert "<script src=" not in html
    assert "<link " not in html
    # Inlined assets
    assert "Cytoscape Consortium" in html  # cytoscape.min.js
    assert "--gold" in html  # viewer.css
    assert "__OKF_ELEMENTS__" in html  # viewer.js
    # Bundle title rendered
    assert "demo" in html


def test_render_html_escapes_script_tag_in_body() -> None:
    elements = [
        {
            "data": {
                "id": "x",
                "label": "X",
                "type": "Memory",
                "tags": [],
                "color": "#4ADE80",
                "size": 30,
                "body": "<script>alert(1)</script>",
            }
        }
    ]
    html = render_html(elements, "t")
    # Closing </script> in embedded JSON must be escaped so it can't break out.
    # The body is <script>alert(1)</script>; in the JSON payload the closing tag
    # becomes <\/script> -- the unescaped literal </script> must not appear
    # anywhere except as a proper HTML tag closer.

    # Count bare </script> occurrences; only the 3 proper closing script tags
    # (cytoscape, elements JSON block, viewer.js block) should be present.
    closing_tags = re.findall(r"</script>", html)
    # The payload's </script> is escaped as <\/script>, so only 3 proper
    # HTML closing tags should exist in the document.
    assert len(closing_tags) == 3
    # The escaped form must be present in the payload.
    assert r"<\/script>" in html


def test_build_viewer_writes_file_at_bundle_root(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text("---\nokf_version: '0.1'\n---\n# Index\n")
    memories = bundle / "memories"
    memories.mkdir()
    (memories / "alpha-abc12345.md").write_text("---\ntype: Memory\ntitle: A\n---\n\nBody.\n")

    out = build_viewer(bundle)
    assert out == bundle / "viewer.html"
    assert out.exists()
    html = out.read_text()
    assert "Cytoscape Consortium" in html
    assert "alpha-abc12345" in html


def test_build_viewer_custom_out_path(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text("---\nokf_version: '0.1'\n---\n# Index\n")
    custom = tmp_path / "elsewhere.html"
    out = build_viewer(bundle, out_path=custom)
    assert out == custom and custom.exists()


def test_render_html_elements_are_valid_json() -> None:
    elements = [
        {
            "data": {
                "id": "a",
                "label": "A",
                "type": "Memory",
                "tags": ["x"],
                "color": "#4ADE80",
                "size": 30,
                "body": "B",
            }
        }
    ]
    html = render_html(elements, "t")
    # Locate the JSON payload and round-trip parse it
    marker = "window.__OKF_ELEMENTS__ = "
    start = html.index(marker) + len(marker)
    end = html.index(";\n", start)
    payload = html[start:end].replace("<\\/", "</")
    assert json.loads(payload) == elements
