"""Regression tests for OM-mcp issue #60.

Gemini's batchEmbedContents endpoint occasionally returns HTTP 200 with
fewer embeddings than items submitted. Before the fix, `_embed_gemini_batch`
silently truncated via zip() and `generate_embeddings_batch` raised
'Embedding batch completed with missing results' AFTER the API call --
no retry. These tests pin the retry semantics.
"""

from unittest.mock import patch

import pytest

from ogham.embeddings import _embed_gemini_batch


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeResponse:
    def __init__(self, vectors):
        self.embeddings = [_FakeEmbedding(v) for v in vectors]
        self.usage_metadata = None


class _ShortThenFullClient:
    """First call returns N-1 embeddings, subsequent calls return N."""

    def __init__(self, full_vectors):
        self._full = full_vectors
        self.calls = 0

        class _Models:
            def embed_content(inner_self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return _FakeResponse(self._full[:-1])
                return _FakeResponse(self._full)

        self.models = _Models()


class _AlwaysShortClient:
    """Every call returns one fewer embedding than requested."""

    def __init__(self, full_vectors):
        self._full = full_vectors
        self.calls = 0

        class _Models:
            def embed_content(inner_self, **kwargs):
                self.calls += 1
                return _FakeResponse(self._full[:-1])

        self.models = _Models()


_VECTORS_3 = [
    [0.1] * 512,
    [0.2] * 512,
    [0.3] * 512,
]


def _settings_with_gemini():
    """Patch settings to make the function entrypoint runnable in tests."""
    from ogham import embeddings as emb_mod

    return patch.multiple(
        emb_mod.settings,
        gemini_api_key="test-key",
        embedding_dim=512,
        gemini_embed_model="gemini-embedding-2",
    )


def test_short_response_triggers_retry_then_succeeds(monkeypatch):
    """A short response on the first call must retry and succeed on the second."""
    client = _ShortThenFullClient(_VECTORS_3)
    from ogham import embeddings as emb_mod

    monkeypatch.setattr(emb_mod, "_get_gemini_client", lambda: client)
    # Shrink retry wait so the test doesn't burn 3+ seconds on backoff
    monkeypatch.setenv("OGHAM_RETRY_FAST", "1")

    with _settings_with_gemini():
        out = _embed_gemini_batch(["a", "b", "c"])

    assert client.calls == 2
    assert len(out) == 3
    assert all(len(v) == 512 for v in out)


def test_persistently_short_response_raises_after_max_attempts(monkeypatch):
    """If Gemini keeps returning short, tenacity must give up with reraise=True."""
    client = _AlwaysShortClient(_VECTORS_3)
    from ogham import embeddings as emb_mod

    monkeypatch.setattr(emb_mod, "_get_gemini_client", lambda: client)
    monkeypatch.setenv("OGHAM_RETRY_FAST", "1")

    with _settings_with_gemini(), pytest.raises(RuntimeError) as exc_info:
        _embed_gemini_batch(["a", "b", "c"])

    msg = str(exc_info.value)
    assert "2" in msg and "3" in msg
    assert "short" in msg.lower() or "missing" in msg.lower()


def test_default_gemini_model_is_ga_alias():
    """Default config must point at the GA alias `gemini-embedding-2`,
    not the soon-to-be-retired `-preview` alias."""
    from ogham.config import Settings

    fresh = Settings(supabase_url="http://x", supabase_key="x")
    assert fresh.gemini_embed_model == "gemini-embedding-2"
