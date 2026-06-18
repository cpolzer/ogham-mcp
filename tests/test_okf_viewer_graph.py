from ogham.okf.viewer.concepts import ViewerConcept
from ogham.okf.viewer.graph import build_elements


def _concept(cid: str, **kw) -> ViewerConcept:
    return ViewerConcept(
        id=cid,
        type=kw.get("type", "Memory"),
        title=kw.get("title", cid),
        tags=kw.get("tags", []),
        body=kw.get("body", ""),
        links_to=kw.get("links_to", []),
    )


def test_nodes_use_palette_color() -> None:
    concepts = [_concept("a", type="Decision"), _concept("b", type="Unknown Type")]
    elements = build_elements(concepts)
    by_id = {e["data"]["id"]: e for e in elements if "source" not in e["data"]}
    assert by_id["a"]["data"]["color"] == "#D4A843"
    assert by_id["b"]["data"]["color"] == "#94a3b8"


def test_node_size_grows_with_body_capped_at_90() -> None:
    short = _concept("s", body="x" * 100)  # 30 + 0 = 30
    medium = _concept("m", body="x" * 4000)  # 30 + 20 = 50
    huge = _concept("h", body="x" * 50000)  # 30 + capped 60 = 90
    elements = build_elements([short, medium, huge])
    sizes = {e["data"]["id"]: e["data"]["size"] for e in elements if "source" not in e["data"]}
    assert sizes == {"s": 30, "m": 50, "h": 90}


def test_edges_only_emitted_between_existing_nodes() -> None:
    concepts = [
        _concept("a", links_to=["b", "ghost"]),
        _concept("b"),
    ]
    elements = build_elements(concepts)
    edges = [e for e in elements if "source" in e["data"]]
    assert len(edges) == 1
    assert edges[0]["data"]["source"] == "a"
    assert edges[0]["data"]["target"] == "b"


def test_edge_ids_are_stable_and_unique() -> None:
    concepts = [
        _concept("a", links_to=["b", "b"]),  # dedup same-target
        _concept("b"),
    ]
    elements = build_elements(concepts)
    edges = [e for e in elements if "source" in e["data"]]
    assert len(edges) == 1
    assert edges[0]["data"]["id"] == "a->b"


def test_tags_passed_through() -> None:
    concepts = [_concept("a", tags=["project:demo", "type:decision"])]
    elements = build_elements(concepts)
    node = next(e for e in elements if "source" not in e["data"])
    assert node["data"]["tags"] == ["project:demo", "type:decision"]
