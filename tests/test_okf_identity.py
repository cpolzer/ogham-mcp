import pytest

from ogham.okf.identity import make_filename, slugify


@pytest.mark.parametrize(
    "content,expected",
    [
        ("Chose UUID PKs over bigint", "chose-uuid-pks-over-bigint"),
        ("HELLO World", "hello-world"),
        ("Multiple   spaces  between", "multiple-spaces-between"),
        ("Special!@#$chars*&^removed", "special-chars-removed"),
        ("Leading and trailing  ", "leading-and-trailing"),
        ("", "untitled"),  # empty content fallback
        ("   ", "untitled"),  # whitespace-only fallback
        ("emoji \U0001f389 stripped", "emoji-stripped"),
    ],
)
def test_slugify_normalises_content(content, expected):
    assert slugify(content) == expected


def test_slugify_caps_at_60_chars():
    long_content = "x" * 100
    result = slugify(long_content)
    assert len(result) <= 60


def test_slugify_does_not_split_words_mid_char():
    content = "The quick brown fox jumps over the lazy dog and then some more text"
    result = slugify(content)
    # Should not end with a partial word
    assert not result.endswith("-")


def test_make_filename_combines_slug_and_uuid8():
    memory = {
        "id": "7da3c025-fa77-4f0b-9d2e-1ab84e6c3f99",
        "content": "Chose UUID PKs over bigint",
    }
    assert make_filename(memory) == "chose-uuid-pks-over-bigint-7da3c025.md"


def test_make_filename_uses_first_8_hex_of_uuid():
    memory = {"id": "abcdef12-3456-7890-abcd-ef1234567890", "content": "x"}
    assert make_filename(memory).endswith("-abcdef12.md")


def test_make_filename_handles_empty_content():
    memory = {"id": "00000000-0000-0000-0000-000000000000", "content": ""}
    assert make_filename(memory) == "untitled-00000000.md"
