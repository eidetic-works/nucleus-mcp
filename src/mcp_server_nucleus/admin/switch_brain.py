"""Brain-preset swapper for an MCP host (Antigravity today; any MCP-config JSON).

Rewrites the host's MCP config so the Nucleus server boots against the
requested brain preset, then kills any currently-running Nucleus processes
so the operator can restart the host cleanly.

Presets:

- ``warm`` / ``prod`` — the live brain (``NUCLEUS_BRAIN_PATH`` or ``.brain``).
- ``cold`` / ``dogfood`` — a disposable brain for clean-slate testing.
  Default lives alongside the repo at ``<NUCLEUS_ROOT>/../dogfood-brain/.brain``;
  override with ``NUCLEUS_TEST_BRAIN``.

Env contract:

- ``NUCLEUS_ANTIGRAVITY_CONFIG`` wins for the host config path.
  Fallback: ``~/.gemini/antigravity/mcp_config.json`` (Antigravity default).
- ``NUCLEUS_BRAIN_PATH`` wins for warm/prod brain path. Fallback: ``.brain``.
- ``NUCLEUS_TEST_BRAIN`` wins for cold/dogfood brain path.
  Fallback: ``<NUCLEUS_ROOT>/../dogfood-brain/.brain`` via ``paths.nucleus_root``.

Usage: ``python -m mcp_server_nucleus.admin.switch_brain [warm|cold|dogfood]``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from mcp_server_nucleus.paths import nucleus_root

_DEFAULT_HOST_CONFIG = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
_NUCLEUS_PROCESS_PATTERN = "mcp_server_nucleus"


def _host_config_path() -> Path:
    env = os.environ.get("NUCLEUS_ANTIGRAVITY_CONFIG")
    if env:
        return Path(env)
    return _DEFAULT_HOST_CONFIG


def _warm_brain() -> str:
    return os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")


def _cold_brain() -> str:
    env = os.environ.get("NUCLEUS_TEST_BRAIN")
    if env:
        return env
    return str(nucleus_root().parent / "dogfood-brain" / ".brain")


def _brains() -> dict[str, str]:
    warm = _warm_brain()
    cold = _cold_brain()
    return {"warm": warm, "prod": warm, "cold": cold, "dogfood": cold}


def _load_config(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: MCP host config not found at {path}", file=sys.stderr)
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def _save_config(path: Path, config: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(config, indent=2))
    os.replace(tmp, path)
    print(f"updated {path}")


def _kill_servers() -> None:
    print(f"killing any running {_NUCLEUS_PROCESS_PATTERN} processes...")
    try:
        subprocess.run(
            ["pkill", "-f", _NUCLEUS_PROCESS_PATTERN], check=False, timeout=5
        )
        time.sleep(1)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"WARN: pkill failed: {exc}")


def switch_brain(mode: str) -> int:
    brains = _brains()
    if mode not in brains:
        print(
            f"ERROR: unknown mode '{mode}'. Available: {', '.join(brains)}",
            file=sys.stderr,
        )
        return 1

    target = brains[mode]
    host_config = _host_config_path()
    print(f"switching to {mode.upper()} brain: {target}")

    _kill_servers()

    try:
        config = _load_config(host_config)
    except FileNotFoundError:
        return 1

    try:
        config["mcpServers"]["nucleus"]["env"]["NUCLEUS_BRAIN_PATH"] = target
    except KeyError:
        print(
            "ERROR: host config missing ['mcpServers']['nucleus']['env']"
            "['NUCLEUS_BRAIN_PATH']",
            file=sys.stderr,
        )
        return 1

    _save_config(host_config, config)

    if mode in ("cold", "dogfood"):
        brain_dir = Path(target)
        if brain_dir.exists():
            print(f"cleaning cold brain at {brain_dir}...")
            shutil.rmtree(brain_dir)
            print("  (deleted old cold-brain state)")

    print("")
    print("=" * 40)
    print(f"SUCCESS: switched to {mode.upper()}.")
    print("ACTION REQUIRED: restart the MCP host now.")
    print("=" * 40)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(
            "Usage: python -m mcp_server_nucleus.admin.switch_brain "
            "[warm|prod|cold|dogfood]",
            file=sys.stderr,
        )
        return 1
    return switch_brain(args[0])


if __name__ == "__main__":
    sys.exit(main())
