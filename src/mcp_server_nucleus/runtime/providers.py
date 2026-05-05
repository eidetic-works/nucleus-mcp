"""
Nucleus Provider Registry — Slice #3 config-registry role_map (2026-04-22).

Declarative source-of-truth for the prefix→provider→role mapping. Replaces
the hardcoded `_PROVIDER_PATTERNS` tuple that lived inline in `sync_ops.py`.
Adding a new provider is a YAML-only edit; zero code changes required.

Per ADR-0005 §D5 grace-period: the coerce API preserves the legacy
signature `(agent_id, role) -> {role, provider, session_id}` so callers
stay green. Primitive-gate axes enforced:

  - any-computer: YAML path overridable via $NUCLEUS_PROVIDERS_YAML
  - any-OS:       stdlib-only parser (no PyYAML dependency required)
  - any-user:     no absolute paths in shipped default
  - any-agent:    provider list is data; any MCP-speaking agent adds
                  itself via YAML entry alone
  - any-LLM:      prefix/provider/role entries are LLM-invariant tokens

Schema (schema_version: 1):

    schema_version: 1
    providers:
      - prefix: <str>        # legacy agent_id prefix (e.g. "claude_code_peer")
        provider: <str>      # canonical provider token (e.g. "anthropic_claude_code")
        default_role: <str>  # fallback role when caller doesn't supply one

Order in the list defines prefix-match priority (first match wins).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

_DEFAULT_YAML_NAME = "providers.yaml"
_ENV_OVERRIDE = "NUCLEUS_PROVIDERS_YAML"

# Thread-safe registry cache keyed by (resolved_path, mtime_ns).
_CACHE_LOCK = Lock()
_CACHE: Dict[Tuple[str, int], "ProviderRegistry"] = {}


@dataclass(frozen=True)
class ProviderEntry:
    """One row in providers.yaml."""

    prefix: str
    provider: str
    default_role: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "prefix": self.prefix,
            "provider": self.provider,
            "default_role": self.default_role,
        }


@dataclass(frozen=True)
class ProviderRegistry:
    """Immutable loaded registry (value object). Schema-validated."""

    schema_version: int
    entries: Tuple[ProviderEntry, ...]
    source_path: str

    def coerce(self, agent_id: str, role: str = "") -> Dict[str, str]:
        """Legacy-signature coerce, preserving `_coerce_legacy_to_tuple` semantics."""
        if not agent_id:
            return {"role": role or "worker", "provider": "unknown", "session_id": ""}
        for entry in self.entries:
            if agent_id.startswith(entry.prefix):
                return {
                    "role": role or entry.default_role,
                    "provider": entry.provider,
                    "session_id": agent_id,
                }
        return {"role": role or "worker", "provider": "unknown", "session_id": agent_id}

    def list_providers(self) -> List[Dict[str, str]]:
        """Enumerate registered providers (for MCP surface / introspection)."""
        return [e.to_dict() for e in self.entries]


# -----------------------------------------------------------------------------
# YAML loading (stdlib-only, no PyYAML required)
# -----------------------------------------------------------------------------


class RegistryLoadError(ValueError):
    """Raised when providers.yaml is malformed or fails schema validation."""


def _default_yaml_path() -> Path:
    """Return the shipped-with-package default path."""
    return Path(__file__).resolve().parent / _DEFAULT_YAML_NAME


def _resolve_yaml_path(explicit: Optional[Path]) -> Path:
    """Resolve the YAML path: explicit arg > env override > shipped default."""
    if explicit is not None:
        return Path(explicit).resolve()
    env = os.environ.get(_ENV_OVERRIDE)
    if env:
        return Path(env).resolve()
    return _default_yaml_path()


_COMMENT_RE = re.compile(r"(^|\s)#.*$")
_ENTRY_KEYS = {"prefix", "provider", "default_role"}


def _strip_comment(line: str) -> str:
    # Remove trailing comments but preserve content; full-line comments
    # collapse to empty.
    stripped = line.rstrip()
    if not stripped:
        return ""
    if stripped.lstrip().startswith("#"):
        return ""
    return _COMMENT_RE.sub("", stripped).rstrip()


def _parse_scalar(raw: str) -> object:
    """Parse a YAML scalar: int, quoted string, or bare string."""
    raw = raw.strip()
    if not raw:
        return ""
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    # Integer detection (schema_version is an int).
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return int(raw)
    return raw


def _parse_yaml(text: str) -> Dict[str, object]:
    """
    Minimal YAML subset parser sufficient for providers.yaml.

    Supports:
      - top-level scalar assignments: `key: value`
      - top-level list-of-dicts: `key:\n  - sub_key: value\n    sub_key: value`
      - comments (`#`) at line start or after scalar
      - blank lines

    Rejects anything else. If PyYAML is available we fall back to it for
    robustness, but the stdlib path is the primary entry point so the
    loader has no external dependency by default.
    """
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            raise RegistryLoadError(
                f"providers.yaml must be a mapping at top level, got {type(loaded).__name__}"
            )
        return loaded
    except ImportError:
        pass  # fall through to stdlib parser

    result: Dict[str, object] = {}
    current_list_key: Optional[str] = None
    current_list: Optional[List[Dict[str, object]]] = None
    current_entry: Optional[Dict[str, object]] = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line)
        if not line:
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            # Top-level key.
            if ":" not in stripped:
                raise RegistryLoadError(
                    f"providers.yaml line {lineno}: expected 'key: value' at top level"
                )
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _parse_scalar(value)
                current_list_key = None
                current_list = None
                current_entry = None
            else:
                # Start of a list or mapping value.
                current_list_key = key
                current_list = []
                result[key] = current_list
                current_entry = None
        elif stripped.startswith("- "):
            if current_list is None:
                raise RegistryLoadError(
                    f"providers.yaml line {lineno}: list item with no parent key"
                )
            # Start a new list entry.
            current_entry = {}
            current_list.append(current_entry)
            inner = stripped[2:].strip()
            if inner:
                if ":" not in inner:
                    raise RegistryLoadError(
                        f"providers.yaml line {lineno}: list item must be a mapping 'key: value'"
                    )
                k, _, v = inner.partition(":")
                current_entry[k.strip()] = _parse_scalar(v)
        else:
            # Continuation line of current list entry.
            if current_entry is None:
                raise RegistryLoadError(
                    f"providers.yaml line {lineno}: indented line with no active list entry"
                )
            if ":" not in stripped:
                raise RegistryLoadError(
                    f"providers.yaml line {lineno}: expected 'key: value' in list entry"
                )
            k, _, v = stripped.partition(":")
            current_entry[k.strip()] = _parse_scalar(v)

    return result


def _validate_schema(loaded: Dict[str, object], source: Path) -> ProviderRegistry:
    """Validate parsed YAML against the expected providers.yaml schema."""
    schema_version = loaded.get("schema_version")
    if schema_version != 1:
        raise RegistryLoadError(
            f"providers.yaml {source}: schema_version must be 1, got {schema_version!r}"
        )

    raw_entries = loaded.get("providers")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RegistryLoadError(
            f"providers.yaml {source}: `providers` must be a non-empty list"
        )

    entries: List[ProviderEntry] = []
    seen_prefixes: set = set()
    for idx, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise RegistryLoadError(
                f"providers.yaml {source}: providers[{idx}] must be a mapping"
            )
        unknown = set(raw.keys()) - _ENTRY_KEYS
        if unknown:
            raise RegistryLoadError(
                f"providers.yaml {source}: providers[{idx}] has unknown keys {sorted(unknown)}"
            )
        missing = _ENTRY_KEYS - set(raw.keys())
        if missing:
            raise RegistryLoadError(
                f"providers.yaml {source}: providers[{idx}] missing required keys {sorted(missing)}"
            )
        prefix = str(raw["prefix"])
        provider = str(raw["provider"])
        default_role = str(raw["default_role"])
        if not prefix or not provider or not default_role:
            raise RegistryLoadError(
                f"providers.yaml {source}: providers[{idx}] has empty required field"
            )
        if prefix in seen_prefixes:
            raise RegistryLoadError(
                f"providers.yaml {source}: duplicate prefix {prefix!r}"
            )
        seen_prefixes.add(prefix)
        entries.append(
            ProviderEntry(prefix=prefix, provider=provider, default_role=default_role)
        )

    return ProviderRegistry(
        schema_version=int(schema_version),
        entries=tuple(entries),
        source_path=str(source),
    )


def load_registry(path: Optional[Path] = None, *, use_cache: bool = True) -> ProviderRegistry:
    """
    Load providers.yaml. Resolution order:

      1. explicit `path` argument
      2. `$NUCLEUS_PROVIDERS_YAML` env var
      3. shipped default at `<package>/runtime/providers.yaml`

    Cached by `(resolved_path, mtime_ns)` so live edits are picked up on
    next call without a process restart.
    """
    resolved = _resolve_yaml_path(path)
    if not resolved.exists():
        raise RegistryLoadError(f"providers.yaml not found at {resolved}")

    mtime_ns = resolved.stat().st_mtime_ns
    cache_key = (str(resolved), mtime_ns)

    if use_cache:
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            if cached is not None:
                return cached

    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as e:
        raise RegistryLoadError(f"providers.yaml {resolved}: read failed: {e}")

    loaded = _parse_yaml(text)
    registry = _validate_schema(loaded, resolved)

    if use_cache:
        with _CACHE_LOCK:
            _CACHE[cache_key] = registry

    return registry


def coerce_to_tuple(
    agent_id: str, role: str = "", *, registry: Optional[ProviderRegistry] = None
) -> Dict[str, str]:
    """
    Registry-backed replacement for `_coerce_legacy_to_tuple`. Signature
    preserved so `sync_ops.py` callers remain green post-refactor.
    """
    if registry is None:
        registry = load_registry()
    return registry.coerce(agent_id, role)


def list_providers(
    *, registry: Optional[ProviderRegistry] = None
) -> List[Dict[str, str]]:
    """Enumerate registered providers. Intended for MCP surface + introspection."""
    if registry is None:
        registry = load_registry()
    return registry.list_providers()


def _clear_cache_for_tests() -> None:
    """Test-only cache reset; not part of the public surface."""
    with _CACHE_LOCK:
        _CACHE.clear()
