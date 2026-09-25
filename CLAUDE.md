# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`nucleus-mcp` — an MCP server (plus a full CLI and SDKs) that gives AI agents a
persistent, file-based brain in a `.brain/` folder. MIT, published to PyPI as
`nucleus-mcp`, public mirror `eidetic-works/nucleus-mcp`.

**This checkout is the development tree — the source of truth.** It lives at
`mcp-server-nucleus/` inside the `ai-mvp-backend-mirror-v2` monorepo, and
`scripts/sync_public_repo.sh` archives *from* here *to* the public repo, one way,
with `git archive` so only committed tracked files move. Everything downstream is
a snapshot. `.gitattributes` marks `tests/`, most of `scripts/`, and the private CI
workflow as `export-ignore`, so those exist here and are absent there.

**A fix made in a snapshot does not survive.** The next sync overwrites it. Land
work here. This is not hypothetical: 44 audit fixes, including every blocker in
`docs/AUDIT_LEDGER.md`, were written against the `nucleus-private` snapshot before
anyone noticed, and had to be ported back (2026-09-12).

**This is also the only tree where "nothing references it" can be established**,
because `tests/` is here. The difference is not marginal. Run in the snapshot,
`tools_audit/screen_dead_modules.py` proposed 34 modules and ~9,880 lines for
deletion. Run here, with `tests/` present, it reports **3 modules and 566 lines**
dead and 30 of the 34 still referenced — `pulse.py` and `swarm.py` among them, both
of which have tests *and*, in pulse's case, a live importer in
`runtime/god_combos/`. A deletion driven by the snapshot's reference count would
have removed tested, imported code. That is exactly why the script refuses to run
without `tests/`; do not override it.

The package ships **two independent MCP servers**: `nucleus` (the brain) and
`nucleus-rabbithole` (a local-SQLite rabbit-hole depth tracker, `docs/RABBITHOLE.md`).
They share a wheel and nothing else.

## Commands

```bash
pip install -e ".[dev]"          # dev install (pytest, ruff, asyncio, benchmark)
ruff check src/                  # the CI lint gate — line-length 100, py310 target
pytest tests/ -v --tb=short      # full suite, only in a tree that has tests/
pytest tests/test_foo.py::TestBar::test_baz   # single test
pytest -m "not e2e and not release"           # skip integration + release-hygiene gates
hatch build                      # wheel + sdist (sdist is fenced to src/ + 4 files)
```

```bash
# The audit regression suites. They live OUTSIDE tests/ on purpose: tests/ is
# export-ignored, so these are the only regression tests that reach a snapshot.
# CI runs all three on every matrix leg. 336 tests.
pytest tests_security tests_onboarding tests_contract -q

# What CI's "Every facade registers" step runs. Fails if any facade is dropped.
NUCLEUS_STRICT_REGISTRATION=true python -c "import mcp_server_nucleus as n; n._ensure_initialized()"
```

**The lint gate is pinned, and was not always.** `pyproject` now sets
`select = ["E4", "E7", "E9", "F"]` and CI installs `ruff==0.15.*`. Before that it
set `ignore` with no `select` against an unpinned ruff, so the effective rule set
moved with each release: a newer default took the job from 5 findings to 7293
without a line of source changing, and `lint` was red on `main` for ten days.
Keep both pins together — changing one without the other reopens that gap.

The ignore list also disables a long tail of rules (`F401`, `F841`, `E722`,
`F811`, `F821`, …) — matching existing style matters more than satisfying a
stricter linter.

Entry points (all defined in `pyproject.toml`): `nucleus` (CLI, ~100 subcommands),
`nucleus-mcp` (stdio server), `nucleus-mcp-http` / `nucleus-mcp-cloud` (HTTP,
Cloud Run), `nucleus-rabbithole`, `nucleus-relay-bridge`, `nucleus-wedge`.

## Architecture

### Facade tools, not 170 tools

Every MCP tool module in `src/mcp_server_nucleus/tools/` exposes **one** facade
function taking `(action: str, params: dict)`. Each module defines a `ROUTER`
dict mapping action names to handlers and delegates to `dispatch` /
`async_dispatch` in `tools/_dispatch.py`, which adds param sanitization,
telemetry, rate limiting and envelope wrapping. Two pre-facade modules
(`cost_router`, `audit_log_tool`) use the thinner `make_response_dispatch` and
deliberately skip that machinery — don't "fix" them into the main path.

Responses are wrapped by `tools/_envelope.py` (`wrap()` / `error_envelope()` /
`unwrap()` — never hand-build the dict). The shape is mirrored as a pinned JSON
Schema at `src/mcp_server_nucleus/schemas/envelope.schema.json`.

**Wrapping is OFF by default**, and only `NUCLEUS_ENVELOPE=on` turns it on —
`true` and `1` do not. So the envelope you read about in that schema is not what
a default deployment actually returns; handlers' raw payloads are. This line
previously said the opposite, copied from a self-contradicting docstring in
`_envelope.py` (ledger CP-6).

### Registration chain

`tools/__init__.py::register_all(mcp, helpers)` imports each active facade module
and calls its `register(mcp, helpers)`, which returns `[(name, func)]` tuples that
get `setattr`'d back onto the `mcp_server_nucleus` package. External callers depend
on that injection contract. Two filters sit in front:

- `NUCLEUS_ACTIVE_MODULES` — comma-separated module whitelist (`_ALL_MODULE_NAMES`).
- `NUCLEUS_TOOL_TIER` (0/1/2, default 2) — `core/tool_registration_impl.py` monkey-patches
  `mcp.tool` so `tool_tiers.py` can drop out-of-tier facades *before* FastMCP sees
  them. Tiering is per-facade, never per-action. The same wrapper hosts the RPC
  firewall hook that blocks writes to watchdog-protected paths.

Registration is deferred, not import-time: `_ensure_initialized()` (aliased
`_ensure_registered`) in `__init__.py` fires it once per process, from `main()`
in either `__init__.py` or `server.py`.

**A facade that fails to register is caught, not fatal — but no longer silent.**
`register_all` still catches per-module so one broken facade cannot stop the
server, and it records what failed in `tools.get_registration_failures()`, logs
it at ERROR, and prints a degraded-start summary that is *not* suppressed by
quiet mode. `NUCLEUS_STRICT_REGISTRATION=true` makes it fatal instead, and CI
runs the whole registration under that flag on every matrix leg. This exists
because the `grounding` facade returned a bare function where the other 17
return `(name, func)` pairs, the bare except swallowed it, and the entire GROUND
surface was missing from every boot while CI printed the error and passed.

### Import-boundary discipline (the main editing hazard)

Package `__init__` files are intentionally lazy, using PEP 562 `__getattr__` to
resolve submodules on first attribute access. A module-level `from .runtime.x import y`
inside `__init__.py` or another core module is a **core→periphery eager import**
that the boundary ratchet hard-fails (ADR-0043 W1). Put such imports inside the
function that needs them; the existing code carries comments explaining each case
(see the telemetry import in `__init__.py`). Adding one eager import can drag the
entire facade/agent-runtime/governance surface into every `import mcp_server_nucleus`.

Related: on the stdio transport **stdout belongs to JSON-RPC**. All diagnostics go
to `sys.stderr` or `logging`. A stray `print()` corrupts the protocol.

### Three path resolvers — pick the right one

- `paths.py` — strict env contract for repo-level paths (`NUCLEUS_ROOT`, `NUCLEUS_BRAIN`,
  `NUCLEUS_TRANSCRIPT_ROOT`), with a `strict=True` mode that raises instead of falling back.
- `runtime/common.py::get_brain_path()` — the runtime resolver used by ~215 call sites.
  Order: per-request contextvar (multi-tenant safe) → project detection when
  `NUCLEUS_PROJECT_SPINE` is on → `NUCLEUS_BRAIN_PATH` → walk up from cwd for `.brain/`.
  The contextvar wins because `os.environ` is process-wide and races across async tenants.
  **Creates the directory if it is missing**, so an absent brain is not an error here.
- `nucleus_wedge/store.py::Store.brain_path()` — a third resolver, and this section used to
  claim there were only two (ledger CN-3). Order: explicit argument → `NUCLEUS_BRAIN_PATH`
  or `NUCLEAR_BRAIN_PATH` → `.brain/` in cwd → `.git/` in cwd → **raise**. Two deliberate
  differences from the one above: it does not walk up to ancestor directories (a
  cwd-binding hazard the wedge spec rules out), and it raises rather than falling back.
  Do not "unify" it into `get_brain_path()` without reading that reasoning — the divergence
  is the point, and the walk-up is what it is avoiding.

**Anything you start on a background thread loses that contextvar.** A plain
`threading.Thread` begins with a fresh `Context`, so `get_brain_path()` inside it
falls through to `os.environ` or a cwd walk and resolves some other tenant's
brain — and the middleware restores those env vars when the request ends, which
makes the window wider, not narrower, since a background thread usually runs
after its request has returned. Use `runtime/common.py::start_tenant_thread`,
which copies the context at the call. Call it from the request context, not from
inside another thread.

**Three** different code paths create a `.brain/`, and no two agree. Check which one
you are on before assuming a directory exists.

| Path | Creates |
|---|---|
| `cli.py::init_brain_default` (`nucleus init`) | `ledger/`, `sessions/`, `slots/`, `artifacts/{research,strategy}/`, `agents/`, `memory/`, `config/`, plus `ledger/state.json`, `ledger/events.jsonl`, `ledger/tasks.json`, `memory/engrams.json` |
| `cli.py::init_brain_v0` (`nucleus init -t v0`) | `decisions/`, `policies/`, `plans/`, `session_mirror/` — no overlap at all with the default |
| `get_brain_path()` tenant fallback | `engrams/`, `tasks/`, `proofs/`, `governance/`, `channels/`, `federation/`, … when a brain path is set but missing |

`http_transport/tenant.py::brain_path_for_tenant` seeds a fourth variant for HTTP
tenants. Nothing reconciles them.

This is less dangerous than it looks, and it was worth checking rather than assuming:
most runtime paths create what they need on demand, so a `v0` brain still round-trips
`nucleus engram write` and `nucleus engram search`. The real cost is that no single
place owns what a brain contains, so you cannot tell from any one of these four what
will actually be on disk. Check before assuming a directory exists; do not assume its
absence means something is broken.

### Memory layers

`memory/facade.py` (`capture`/`recall`/`curate`) over `memory/sor.py`, a WAL SQLite
store-of-record at `.brain/engrams.db` with an FTS5 shadow table. Both are **scaffold
behind `NUCLEUS_MEMORY_SOR` (default off)** — flag off means no store is constructed
and no file is created. `src/nucleus_wedge/` is a separate, deliberately slim
remember/recall store (BM25) whose schema the SoR was modelled on; keep them distinct.

### Transports and surfaces

stdio (`server.py`) is the default. `http_transport/` carries the Streamable-HTTP /
Cloud Run app, Clerk auth, tenant resolution and the relay route; the hosted relay at
`relay.nucleusos.dev` is what no-install clients (ChatGPT, Claude.ai) connect to.
`sdk/python` and `sdk/typescript` are thin relay clients sharing one envelope format.
`extensions/nucleus-bridge` is a VS Code extension — `NUCLEUS_REF.md` explains why it
must exist alongside MCP (IDE UI control, passive event siphoning) and documents the
three-tier prompt-injection degradation for sandboxed forks.

MCP resources are exposed as `brain://` URIs (`state`, `events`, `context`, `health`,
`changes`, `traces`, …) registered in `server.py::register_resources`; `brain://changes`
is the staleness ledger clients poll.

### HTTP auth, in one place

`docs/AUTH_ARCHITECTURE.md` describes the whole thing and is current. Two shapes
to know before editing here:

- **`NUCLEUS_OAUTH_ENABLED` is three-state, deliberately.** Explicit `false`
  closes the OAuth surface (404), explicit `true` serves it, and **unset serves
  it with one warning per process**. Not an oversight: the live relay runs with
  the variable unset, so a two-state gate would have 404'd Connector sign-in on
  deploy. Do not "tidy" it into a boolean.
- **`runtime/auth/` does not authenticate HTTP requests.** `http_transport/`
  imports nothing from it. `jwt_provider.py` implements real RS256 verification
  and never runs; it is reachable by import but dead by use, so a
  reference-counting dead-code scan will not flag it. Both it and the http/sse
  branch of `auth_manager` carry headers saying so.

## Conventions in this codebase

- **Flag-gated changes with a byte-identical OFF path.** New subsystems land behind a
  `NUCLEUS_*` env flag that defaults off, with the docstring stating exactly what the
  off path does. Follow that when adding anything structural.
- **Comments cite provenance** — ADR numbers (`docs/adr/…` in the full tree), sweep
  dates, PR numbers, and the failure a guard prevents. Preserve these when editing
  nearby code; they are the only record of why a lazy import or fallback exists.
- **Refactors declare their behavioural contract** ("pure refactor: output is
  byte-identical"). Say so explicitly, or say what changed.
- Dead code is removed with a dated note naming the sweep and the evidence
  (see the pruning comment at the top of `tools/__init__.py`).

## Known defects

`docs/AUDIT_LEDGER.md` is the live record of audited, evidence-backed defects and the
work they imply — stable IDs, per-item status, a themed plan and an ordered sequence.
Read it before starting work in this repo: it will tell you whether the thing you are
about to fix is already known, already parked with a reason, or about to be deleted.
Append new findings there rather than starting a new list, and update an item's status
in place when work lands, naming the commit.

## Doc map

`docs/SPECIFICATION.md` (task/orchestration model), `docs/CLI_REFERENCE.md`,
`docs/architecture/` (DSoR, tool-router pattern), `docs/agent_adapter_contract.md`
and `docs/relay_bus_contract.md` (what a conforming client must do: poll inbox at
turn 0, ack every envelope, always pass an explicit `sender`), `docs/AUTH_ARCHITECTURE.md`,
`docs/GOVERNANCE_POLICIES.md`, `NUCLEUS_REF.md`, `SKILL.md` (the CLI surface agents
are told about).
