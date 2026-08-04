# Vendor Shim — How to Run Any Vendor/Model Through the Shim

> **Reference:** operational guide for dispatching cross-vendor work through the
> Nucleus vendor shim. The shim lets you run any vendor (agy/Gemini, devin/GLM,
> claude/Anthropic) through a local proxy at zero cost when the stub LLM is active.

---

## 1. Start the shim

```bash
bash scripts/vendor_shim_ctl.sh start 8787
bash scripts/vendor_shim_ctl.sh status
```

The shim listens on `http://127.0.0.1:8787`. Check with `status` before dispatching.

## 2. Default-model dispatch (CLI)

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:8787 nucleus dispatch <vendor> \
    --prompt-file <path> \
    --timeout <n>
```

- `vendor` is `agy` (Gemini, default `gemini-3.1-pro-high`) or `devin` (GLM, default `glm-5.2`)
- No `--model` flag exists in the CLI — it always uses the vendor's default model

## 3. Non-default model (Python API)

The CLI can't select a non-default model (e.g. `devin/swe-1.7`, `agy/claude-sonnet-4-6`).
Call the Python API directly:

```python
from mcp_server_nucleus.runtime.vendor_dispatch import dispatch_and_capture

dispatch_and_capture(
    vendor="devin",
    prompt=text,
    artifact_ref=None,
    to_role="peer",
    model="swe-1.7",      # non-default model
    mode="write",
    timeout_s=280,
)
```

## 4. Always run in background

Dispatches take 2-15 minutes. Always run in background (`&`) and set a timeout
guard rather than blocking.

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:8787 nucleus dispatch devin \
    --prompt-file /tmp/task.txt \
    --timeout 280 &
```

---

## Via nucleus_delegate MCP tool (alternative to CLI)

The `nucleus_delegate` MCP tool wraps the same dispatch logic with automatic
per-vendor permission flags, output capture, and status reporting:

```
nucleus_delegate(action="dispatch", params={
    "vendor": "devin",
    "model": "glm-5.2",        # optional, defaults to vendor default
    "mode": "write",            # or "read"
    "prompt": "...",
    "artifact_ref": "src/foo.py",
    "expect_paths": ["src/foo.py"],
})
```

This is the preferred path when calling from an MCP-connected agent (Devin,
Claude Code, etc.) — it handles the vendor flags and captures output
synchronously.

---

## Shim + stub LLM = zero cost

When `NUCLEUS_AGENT_OS_STUB_LLM=1` is set, the shim produces deterministic
responses without calling any real LLM API. The referee still verifies claims
with REAL deterministic anchors (git, filesystem, witnesses), so the
verification signal is genuine even at zero API cost.

See `scripts/launch_shim_agents.py` for a working example: 10 simulated vendor
agents, 50 turns, $0.00 API cost, 30 CONFIRMED + 10 PARTIAL, 0 false CONFIRMED.
