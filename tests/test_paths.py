"""Tests for mcp_server_nucleus.paths — env-driven, no user hardcodes.

Gate: env-var-missing strict mode must raise, not silently fall back. That's
the Nucleus-primitive contract — shipped code fails loud on misconfiguration
instead of running against some accidental $HOME.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_server_nucleus.paths import (
    NucleusPathError,
    brain_path,
    nucleus_root,
    transcript_root,
)

_ENV_KEYS = ("NUCLEUS_ROOT", "NUCLEUS_BRAIN", "NUCLEUS_TRANSCRIPT_ROOT")


@pytest.fixture
def clean_env(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_nucleus_root_from_env(clean_env, tmp_path):
    clean_env.setenv("NUCLEUS_ROOT", str(tmp_path))
    assert nucleus_root() == tmp_path


def test_nucleus_root_strict_raises_when_unset(clean_env):
    with pytest.raises(NucleusPathError, match="NUCLEUS_ROOT"):
        nucleus_root(strict=True)


def test_nucleus_root_fallback_non_strict(clean_env):
    assert nucleus_root() == Path.home() / "ai-mvp-backend"


def test_brain_path_from_env(clean_env, tmp_path):
    clean_env.setenv("NUCLEUS_BRAIN", str(tmp_path / "brain"))
    assert brain_path() == tmp_path / "brain"


def test_brain_path_strict_raises_when_unset(clean_env):
    with pytest.raises(NucleusPathError, match="NUCLEUS_BRAIN"):
        brain_path(strict=True)


def test_brain_path_derives_from_nucleus_root(clean_env, tmp_path):
    clean_env.setenv("NUCLEUS_ROOT", str(tmp_path))
    assert brain_path() == tmp_path / ".brain"


def test_transcript_root_from_env(clean_env, tmp_path):
    clean_env.setenv("NUCLEUS_TRANSCRIPT_ROOT", str(tmp_path / "peer"))
    assert transcript_root() == tmp_path / "peer"


def test_transcript_root_strict_raises_when_unset(clean_env):
    with pytest.raises(NucleusPathError, match="NUCLEUS_TRANSCRIPT_ROOT"):
        transcript_root(strict=True)


def test_transcript_root_none_when_unset(clean_env):
    assert transcript_root() is None
