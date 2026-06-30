import pytest
import yaml

from ogham.okf.serialization import read_concept, write_concept


def test_write_concept_emits_yaml_frontmatter_and_body(tmp_path):
    path = tmp_path / "concept.md"
    frontmatter = {"type": "Decision", "id": "abc-123", "tags": ["x", "y"]}
    body = "# Heading\n\nMemory body content."
    write_concept(path, frontmatter, body)

    text = path.read_text(encoding="utf-8")
    # Must open and close with --- delimiters
    assert text.startswith("---\n")
    # Frontmatter block followed by body, separated by closing ---
    assert "\n---\n" in text
    # Body content is preserved verbatim
    assert text.rstrip().endswith("Memory body content.")


def test_write_concept_yaml_is_parseable(tmp_path):
    path = tmp_path / "concept.md"
    frontmatter = {"type": "Decision", "id": "abc-123", "tags": ["x", "y"]}
    write_concept(path, frontmatter, "body text")

    text = path.read_text(encoding="utf-8")
    # Extract block between first two --- lines
    parts = text.split("---\n", 2)
    assert len(parts) >= 3  # ["", yaml_block, body]
    parsed = yaml.safe_load(parts[1])
    assert parsed["type"] == "Decision"
    assert parsed["id"] == "abc-123"
    assert parsed["tags"] == ["x", "y"]


def test_read_concept_round_trip(tmp_path):
    path = tmp_path / "concept.md"
    fm_in = {"type": "Pattern", "id": "xyz", "tags": ["a"]}
    body_in = "# Title\n\nbody here"
    write_concept(path, fm_in, body_in)

    fm_out, body_out = read_concept(path)
    assert fm_out == fm_in
    assert body_out == body_in


def test_read_concept_preserves_body_without_trailing_newline_drift(tmp_path):
    """Multiple write→read cycles must not accumulate trailing newlines."""
    path = tmp_path / "concept.md"
    fm = {"type": "Memory", "id": "aaa", "tags": []}
    body_original = "line one\nline two"

    # First cycle
    write_concept(path, fm, body_original)
    _, body_after_first_read = read_concept(path)
    assert body_after_first_read == body_original, "first read mutated body"

    # Second cycle — write what we just read back, then read again
    write_concept(path, fm, body_after_first_read)
    _, body_after_second_read = read_concept(path)
    assert body_after_second_read == body_original, "second cycle drifted from original"


def test_read_concept_rejects_missing_frontmatter(tmp_path):
    path = tmp_path / "no_fm.md"
    path.write_text("body only no frontmatter\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        read_concept(path)


def test_read_concept_rejects_unparseable_frontmatter(tmp_path):
    path = tmp_path / "bad_fm.md"
    path.write_text("---\nnot: valid: yaml: structure\n---\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError, match="parse"):
        read_concept(path)
