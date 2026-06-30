"""Parity gates for the shared-data artifact (shared/).

These tests are the Python-side mirror of
ogham-cli/internal/native/shared/shared_test.go. Together they hold
the cross-stack contract: hooks_config.yaml + schema.yaml must hash
to the manifest constants below, and all secret-detection regexes
must compile under Python's `re` (a superset of Go's RE2, which the
Go tests pin strictly).

Bump alongside any new shared-data-vX.Y.Z tag.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml

SHARED_DIR = Path(__file__).resolve().parent.parent / "shared"

# Manifest of expected SHA-256 hashes for shared-data-v0.1.0.
EXPECTED_HASHES = {
    "hooks_config.yaml": "40eecf6de03c8659bc4dd3f5225b448db8d0127d0528ca3ad526fee92829da14",
    "schema.yaml": "bd1aa1bec8f5e981041d673daf4fc3f16fa1c19251b6d0710cde61926a4aa0a9",
}


@pytest.mark.parametrize("filename,expected", EXPECTED_HASHES.items())
def test_sha256_parity(filename: str, expected: str) -> None:
    """shared/<file> must hash to the manifest entry for v0.1.0.

    A mismatch means the dev tree drifted from the published
    shared-data-vX.Y.Z tag. Either revert the local change or bump
    shared/schema.yaml's `version:` field, cut a new tag, and update
    the manifests in both consumers.
    """
    path = SHARED_DIR / filename
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (
        f"\n  {filename} SHA-256 drift"
        f"\n    expected: {expected}"
        f"\n    actual:   {actual}"
        f"\n  shared/ has drifted from the shared-data tag manifest. Either"
        f"\n  revert the local edit or cut a new shared-data version and"
        f"\n  update EXPECTED_HASHES."
    )


def test_schema_declares_re2_dialect() -> None:
    schema = yaml.safe_load((SHARED_DIR / "schema.yaml").read_text())
    assert schema.get("regex_dialect") == "re2"
    assert schema.get("version"), "schema.yaml is missing a version: field"


def test_hooks_config_loads_with_expected_keys() -> None:
    cfg = yaml.safe_load((SHARED_DIR / "hooks_config.yaml").read_text())
    assert "signals" in cfg
    assert "secrets" in cfg
    assert "bare_tokens" in cfg["secrets"]
    assert len(cfg["secrets"]["bare_tokens"]) >= 40, "expected >=40 bare-token patterns"


def test_all_secret_patterns_compile() -> None:
    """Loose parity with the Go-side RE2 strict gate.

    Python's `re` is a PCRE superset that accepts RE2 syntax plus
    backreferences and lookarounds; if a pattern compiles here AND
    in Go's regexp engine (TestSecretPatternsCompileAsRE2), it's
    RE2-pure. This Python-side check catches yaml-mangling and
    obvious typos.
    """
    cfg = yaml.safe_load((SHARED_DIR / "hooks_config.yaml").read_text())
    failures: list[tuple[str, str, str]] = []
    for entry in cfg["secrets"]["bare_tokens"]:
        name = entry["name"]
        pat = entry["pattern"]
        try:
            re.compile(pat)
        except re.error as exc:
            failures.append((name, pat, str(exc)))
    assert not failures, "pattern(s) failed to compile in Python's re engine:\n" + "\n".join(
        f"  {n}: {p!r} -- {e}" for n, p, e in failures
    )
