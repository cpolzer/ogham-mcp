"""Tests for ogham.data.loader -- language data loading with caching.

Includes PICT-generated pairwise test cases covering 11 representative
languages × 11 word list types × 3 operations (load/fallback/cache_hit).
"""

import pytest

from ogham.data.loader import (
    _available_languages,
    _load_language_file,
    get_all_day_names,
    get_architecture_words,
    get_compression_decision_words,
    get_day_names,
    get_decision_words,
    get_direction_words,
    get_error_words,
    get_every_words,
    get_month_names,
    get_query_hints,
    get_temporal_keywords,
    get_word_numbers,
    invalidate_cache,
)

# --- Original unit tests ---


def test_load_english():
    """en.yaml loads and day_names has 7 entries (Sun-Sat)."""
    invalidate_cache()
    days = get_day_names("en")
    assert len(days) == 7
    assert days["monday"] == 1
    assert days["sunday"] == 0
    assert days["saturday"] == 6


def test_fallback_to_english():
    """Requesting a nonexistent language falls back to English data."""
    invalidate_cache()
    days = get_day_names("xx")
    assert len(days) == 7
    assert days["monday"] == 1


def test_cache_hit():
    """Second call uses cache -- verify via lru_cache stats."""
    invalidate_cache()
    _load_language_file("en")
    _load_language_file("en")
    info = _load_language_file.cache_info()
    assert info.hits >= 1


def test_invalidate_cache():
    """Cache clears correctly -- misses reset after invalidation."""
    _load_language_file("en")
    invalidate_cache()
    info = _load_language_file.cache_info()
    assert info.currsize == 0


def test_get_all_day_names():
    """get_all_day_names returns merged dict from all available languages."""
    invalidate_cache()
    all_days = get_all_day_names()
    # Must include English entries at minimum
    assert "monday" in all_days
    assert all_days["monday"] == 1
    # Should have at least 7 entries (English alone)
    assert len(all_days) >= 7


def test_get_query_hints():
    """get_query_hints returns list of hint strings."""
    invalidate_cache()
    multi_hop = get_query_hints("en", "multi_hop")
    assert isinstance(multi_hop, list)
    assert len(multi_hop) > 0
    assert "how many" in multi_hop

    # All hints (no type filter)
    all_hints = get_query_hints("en")
    assert isinstance(all_hints, list)
    assert len(all_hints) >= len(multi_hop)
    assert "chronological" in all_hints


# --- Coverage: all 18 YAML files load without error ---

ALL_LANGUAGES = [
    "ar",
    "de",
    "en",
    "es",
    "fr",
    "ga",
    "hi",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "pt-br",
    "ru",
    "tr",
    "uk",
    "zh",
]


@pytest.mark.parametrize("lang", ALL_LANGUAGES)
def test_yaml_loads(lang):
    """Every language YAML file loads and produces a dict with day_names."""
    invalidate_cache()
    data = _load_language_file(lang)
    assert isinstance(data, dict)
    assert "day_names" in data
    assert len(data["day_names"]) >= 7


def test_available_languages_complete():
    """All 18 expected languages are available."""
    langs = set(_available_languages())
    assert langs == set(ALL_LANGUAGES)


# --- PICT-generated pairwise tests ---
# 11 representative languages × 11 word list types × 3 operations
# Equivalence classes: en (primary), de (diacritics), fr (accents),
# pt-br (variant), ru (cyrillic), zh (hanzi), ja (kana), ko (hangul),
# ar (RTL), hi (devanagari), ga (celtic)

ACCESSOR_MAP = {
    "day_names": get_day_names,
    "every_words": get_every_words,
    "temporal_keywords": get_temporal_keywords,
    "direction_words": get_direction_words,
    "decision_words": get_decision_words,
    "error_words": get_error_words,
    "architecture_words": get_architecture_words,
    "month_names": get_month_names,
    "word_numbers": get_word_numbers,
    "query_hints": get_query_hints,
    "compression_decision_words": get_compression_decision_words,
}

FORMAT_MAP = {
    "day_names": dict,
    "month_names": dict,
    "word_numbers": dict,
    "direction_words": dict,
    "query_hints": list,  # get_query_hints() without hint_type returns flat list
    "every_words": list,
    "temporal_keywords": list,
    "decision_words": list,
    "error_words": list,
    "architecture_words": list,
    "compression_decision_words": list,
}

# fmt: off
PICT_CASES = [
    # (language, word_list_type, operation)
    # Generated with pairwise coverage: 11 langs × 11 types × 3 ops
    ("ga", "every_words", "load"),
    ("ar", "architecture_words", "fallback"),
    ("ko", "word_numbers", "cache_hit"),
    ("zh", "query_hints", "load"),
    ("fr", "error_words", "fallback"),
    ("pt-br", "query_hints", "fallback"),
    ("ru", "every_words", "cache_hit"),
    ("zh", "compression_decision_words", "cache_hit"),
    ("en", "decision_words", "cache_hit"),
    ("ko", "every_words", "fallback"),
    ("ar", "day_names", "cache_hit"),
    ("fr", "temporal_keywords", "cache_hit"),
    ("ar", "direction_words", "load"),
    ("hi", "temporal_keywords", "load"),
    ("pt-br", "decision_words", "load"),
    ("ja", "direction_words", "fallback"),
    ("ga", "day_names", "fallback"),
    ("de", "word_numbers", "load"),
    ("hi", "query_hints", "cache_hit"),
    ("ga", "month_names", "cache_hit"),
    ("en", "month_names", "load"),
    ("ru", "day_names", "load"),
    ("ja", "architecture_words", "load"),
    ("zh", "decision_words", "fallback"),
    ("fr", "compression_decision_words", "load"),
    ("de", "direction_words", "cache_hit"),
    ("hi", "compression_decision_words", "fallback"),
    ("ru", "word_numbers", "fallback"),
    ("pt-br", "architecture_words", "cache_hit"),
    ("de", "temporal_keywords", "fallback"),
    ("ko", "error_words", "load"),
    ("ja", "error_words", "cache_hit"),
    ("fr", "month_names", "fallback"),
    ("en", "every_words", "load"),
    ("ar", "compression_decision_words", "cache_hit"),
    ("de", "query_hints", "cache_hit"),
    ("en", "day_names", "load"),
    ("ga", "decision_words", "load"),
    ("pt-br", "month_names", "load"),
    ("ar", "every_words", "load"),
    ("ja", "every_words", "fallback"),
    ("pt-br", "temporal_keywords", "cache_hit"),
    ("en", "architecture_words", "cache_hit"),
    ("hi", "word_numbers", "cache_hit"),
    ("zh", "direction_words", "load"),
    ("ga", "error_words", "load"),
    ("hi", "direction_words", "fallback"),
    ("en", "word_numbers", "cache_hit"),
    ("ja", "query_hints", "load"),
    ("ja", "compression_decision_words", "cache_hit"),
    ("de", "day_names", "load"),
    ("ko", "temporal_keywords", "load"),
    ("de", "compression_decision_words", "cache_hit"),
    ("de", "decision_words", "fallback"),
    ("ko", "query_hints", "fallback"),
    ("zh", "day_names", "fallback"),
    ("zh", "error_words", "load"),
    ("ga", "word_numbers", "load"),
    ("pt-br", "day_names", "cache_hit"),
    ("ru", "month_names", "fallback"),
    ("ru", "compression_decision_words", "cache_hit"),
    ("fr", "query_hints", "fallback"),
    ("pt-br", "direction_words", "load"),
    ("ja", "decision_words", "load"),
    ("ko", "day_names", "fallback"),
    ("en", "direction_words", "load"),
    ("hi", "decision_words", "load"),
    ("fr", "day_names", "load"),
    ("hi", "every_words", "load"),
    ("ga", "direction_words", "cache_hit"),
    ("ru", "error_words", "load"),
    ("fr", "decision_words", "fallback"),
    ("ar", "word_numbers", "load"),
    ("hi", "error_words", "load"),
    ("de", "month_names", "load"),
    ("fr", "architecture_words", "fallback"),
    ("hi", "architecture_words", "cache_hit"),
    ("ru", "decision_words", "load"),
    ("ja", "month_names", "load"),
    ("ja", "word_numbers", "cache_hit"),
    ("zh", "temporal_keywords", "fallback"),
    ("pt-br", "compression_decision_words", "load"),
    ("zh", "every_words", "load"),
    ("ga", "compression_decision_words", "cache_hit"),
    ("ko", "decision_words", "fallback"),
    ("zh", "architecture_words", "load"),
    ("ru", "temporal_keywords", "fallback"),
    ("ar", "decision_words", "cache_hit"),
    ("ko", "month_names", "load"),
    ("ja", "temporal_keywords", "fallback"),
    ("de", "architecture_words", "cache_hit"),
    ("ga", "query_hints", "load"),
    ("en", "temporal_keywords", "load"),
    ("ko", "architecture_words", "cache_hit"),
    ("ga", "architecture_words", "cache_hit"),
    ("ru", "direction_words", "fallback"),
    ("de", "error_words", "load"),
    ("ar", "error_words", "load"),
    ("de", "every_words", "load"),
    ("ar", "month_names", "load"),
    ("ru", "architecture_words", "load"),
    ("fr", "direction_words", "load"),
    ("zh", "word_numbers", "cache_hit"),
    ("fr", "word_numbers", "fallback"),
    ("hi", "day_names", "load"),
    ("en", "compression_decision_words", "load"),
    ("ru", "query_hints", "load"),
    ("hi", "month_names", "fallback"),
    ("fr", "every_words", "fallback"),
    ("pt-br", "every_words", "cache_hit"),
    ("ja", "day_names", "fallback"),
    ("ga", "temporal_keywords", "cache_hit"),
    ("pt-br", "word_numbers", "cache_hit"),
    ("zh", "month_names", "cache_hit"),
    ("ko", "compression_decision_words", "cache_hit"),
    ("pt-br", "error_words", "load"),
    ("ar", "temporal_keywords", "fallback"),
    ("en", "query_hints", "load"),
    ("en", "error_words", "load"),
    ("ar", "query_hints", "fallback"),
    ("ko", "direction_words", "fallback"),
]
# fmt: on


@pytest.mark.parametrize("lang,wlt,operation", PICT_CASES)
def test_pict_loader(lang, wlt, operation):
    """PICT pairwise test: load word list for language with given operation."""
    invalidate_cache()
    accessor = ACCESSOR_MAP[wlt]
    expected_type = FORMAT_MAP[wlt]

    if operation == "fallback":
        # Test that a nonexistent language falls back to English
        result_fallback = accessor("xx_nonexistent")
        result_en = accessor("en")
        assert result_fallback == result_en, f"Fallback mismatch for {wlt}"
        # Also verify the real language loads (separate from fallback test)
        result = accessor(lang)
    elif operation == "cache_hit":
        # First load populates cache, second should hit
        invalidate_cache()
        accessor(lang)
        accessor(lang)
        info = _load_language_file.cache_info()
        assert info.hits >= 1, f"Expected cache hit for {lang}/{wlt}"
        result = accessor(lang)
    else:  # load
        result = accessor(lang)

    # Type check
    assert isinstance(result, expected_type), (
        f"{wlt} for {lang}: expected {expected_type.__name__}, got {type(result).__name__}"
    )

    # Non-empty check (English always has data; others may fall back)
    if lang == "en":
        assert len(result) > 0, f"English {wlt} must not be empty"
