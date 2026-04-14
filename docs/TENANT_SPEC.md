# Nucleus Tenant Isolation Specification

## Overview

Tenant isolation in Nucleus partitions every storage read and write by a resolved `tenant_id` so that no request can access, corrupt, or infer data belonging to another tenant. Isolation is enforced at the brain-path level: each tenant receives an exclusive filesystem subtree, and all tool operations are scoped to that subtree for the lifetime of the request. The model guarantees brain-path separation and token-based authentication; it does not guarantee network-level isolation, per-tenant rate limiting, or billing separation — those are the responsibility of the deployment layer.

---

## Concepts

**tenant_id** — A short, URL-safe string that uniquely identifies a tenant within a deployment. Examples: `"acme"`, `"default"`, `"user-42"`. The resolved `tenant_id` determines every file path the request may touch.

**brain path** — The absolute filesystem path assigned to a tenant for a given request: `NUCLEUS_BRAIN_ROOT / tenant_id / ".brain"`. All tool reads and writes are confined to this directory.

**tenant map** — A mapping from bearer token strings to tenant identities. Supplied via `NUCLEUS_TENANT_MAP` as an inline JSON string or a path to a JSON file. Two formats are supported (see Token Map Formats). Re-read on every request; no server restart is required to update it.

**revocation list** — A set of token strings that are immediately rejected regardless of expiry or map membership. Supplied via `NUCLEUS_REVOKED_TOKENS`. Re-read on every request.

**brain root** — The parent directory under which all per-tenant brain directories are created. Default: `~/.nucleus/tenants`. Overridden by `NUCLEUS_BRAIN_ROOT`.

---

## Tenant Resolution Algorithm

The following procedure is executed once per inbound request, in strict priority order. The first branch that produces a `tenant_id` terminates the algorithm; subsequent branches are not evaluated.

```
function resolve_tenant(request) -> tenant_id:

    # 1. Bearer token — authenticated multi-tenant path
    token = extract_bearer(request.headers.get("Authorization"))
    if token is not None:
        tenant_map = load_tenant_map()          # reads NUCLEUS_TENANT_MAP; re-read every call
        if tenant_map is not None:
            if token in revocation_list():      # reads NUCLEUS_REVOKED_TOKENS; re-read every call
                raise HTTP401("token revoked")
            if token not in tenant_map:
                raise HTTP401("unknown token")
            entry = tenant_map[token]
            if is_expired(entry):               # checks "expires" field if present
                raise HTTP401("token expired")
            return entry.tenant_id

    # 2. Trusted internal header — no token validation
    header_tid = request.headers.get("X-Nucleus-Tenant-ID")
    if header_tid is not None:
        return header_tid

    # 3. Static single-tenant environment variable
    env_tid = os.environ.get("NUCLEUS_TENANT_ID")
    if env_tid is not None:
        return env_tid

    # 4. Solo fallback
    return "default"
```

**Notes on step 1:** If `NUCLEUS_TENANT_MAP` resolves to a non-empty map, any bearer token absent from the map is rejected (401). A deployment that sets a tenant map implicitly requires all authenticated callers to be in it. If `NUCLEUS_TENANT_MAP` is unset or empty, bearer tokens are ignored and resolution falls through to step 2.

**Notes on step 2:** `X-Nucleus-Tenant-ID` is a trusted header intended for internal proxy or sidecar routing where the caller has already been authenticated upstream. Do not expose this header to untrusted clients.

**Notes on expiry:** The `expires` field, if present, is an ISO 8601 UTC timestamp. A token is expired if `utcnow() >= expires`. Absent field means no expiry.

---

## Brain Path Isolation

**Formula:**

```
brain_path = NUCLEUS_BRAIN_ROOT / tenant_id / ".brain"
```

**Default `NUCLEUS_BRAIN_ROOT`:** `~/.nucleus/tenants`

The brain directory is created on first access. On creation, the following subdirectories are initialized:

```
.brain/
  engrams/        # persistent memory (engram ledger)
  sessions/       # session snapshots
  tasks/          # task queue state
  archive/        # training pairs (SFT + DPO), delta log
  audit/          # DSoR audit trail
  governance/     # kill switch, compliance config
  ipc/            # inter-process coordination (locks, tokens)
```

**Contract:** No tool in Nucleus reads from or writes to any path outside its resolved brain path for the duration of a request. Path construction always uses `os.path.join(brain_path, ...)` with the resolved `brain_path`; no user-supplied path components escape the brain root via traversal (e.g., `../` sequences are rejected).

Brain path is injected into the request context via `os.environ["NUCLEUS_BRAIN_PATH"]` before any tool handler executes. This is safe for single-threaded async execution (see Concurrency Contract).

---

## Token Map Formats

### Simple format

```json
{"token-string": "tenant_id"}
```

Each key is a bearer token string; each value is the `tenant_id` to assign.

### Extended format (with expiry)

```json
{
  "token-string": {
    "tenant": "tenant_id",
    "expires": "2026-12-31T00:00:00Z"
  }
}
```

The `tenant` field is required. The `expires` field is optional; if absent, the token does not expire.

### Supplying the map

`NUCLEUS_TENANT_MAP` accepts either:

- **Inline JSON string** — the full JSON object as a single-line string: `NUCLEUS_TENANT_MAP='{"tok1":"acme","tok2":"beta"}'`
- **File path** — an absolute path to a JSON file containing the map: `NUCLEUS_TENANT_MAP=/etc/nucleus/tenant_map.json`

The map is re-read on every inbound request. To rotate or revoke tokens, update the file or env var; no server restart is required.

---

## Revocation

`NUCLEUS_REVOKED_TOKENS` specifies tokens that are unconditionally rejected before any other validation.

**Accepted formats:**

- Comma-separated string: `NUCLEUS_REVOKED_TOKENS="tok-abc,tok-def,tok-ghi"`
- JSON array string: `NUCLEUS_REVOKED_TOKENS='["tok-abc","tok-def"]'`

Revoked tokens return HTTP 401 immediately, before expiry check and before tenant_id resolution. The revocation list is re-read on every request; no server restart is required to take effect.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `NUCLEUS_BRAIN_ROOT` | `~/.nucleus/tenants` | Parent directory for all per-tenant brain directories. |
| `NUCLEUS_BRAIN_PATH` | *(derived)* | Absolute path to the active brain for the current request. Set automatically; do not set manually unless bypassing tenant resolution entirely. |
| `NUCLEUS_TENANT_ID` | *(unset)* | Static tenant ID for single-tenant deployments. Used when no bearer token or `X-Nucleus-Tenant-ID` header is present. |
| `NUCLEUS_TENANT_MAP` | *(unset)* | Inline JSON string or file path mapping bearer tokens to tenant IDs. Enables multi-tenant and SaaS modes. |
| `NUCLEUS_REVOKED_TOKENS` | *(unset)* | Comma-separated or JSON array of bearer token strings to reject immediately (401). |
| `NUCLEUS_HTTP_HOST` | `127.0.0.1` | Bind address for `nucleus-mcp-http`. |
| `NUCLEUS_HTTP_PORT` | `8766` | Bind port for `nucleus-mcp-http`. |

---

## Deployment Modes

| Mode | Configuration Required | Use Case | Isolation Level |
|---|---|---|---|
| **Solo** | None (all defaults) | Local dev, single user, same as stdio but HTTP-accessible | Single brain at `~/.nucleus/tenants/default/.brain` |
| **Single-tenant** | `NUCLEUS_TENANT_ID=<id>` | One org or team on a shared server or Cloud Run instance | Single named brain; no token auth |
| **Multi-tenant** | `NUCLEUS_TENANT_MAP=<map>` | Team deployments, internal SaaS, per-user isolation | Per-token brain, full resolution algorithm active |
| **SaaS** | `NUCLEUS_TENANT_MAP=<map>` + `NUCLEUS_REVOKED_TOKENS` + external proxy auth | Public-facing product with per-customer isolation | Per-token brain + revocation; network/billing isolation is deployment-layer responsibility |

---

## Concurrency Contract

`os.environ["NUCLEUS_BRAIN_PATH"]` is mutated per-request to inject the resolved brain path into tool handlers. This approach is safe under **single-threaded async** execution (the uvicorn default with one worker), because only one coroutine runs at a time between `await` points and no tool handler yields while holding a mutated env state.

This approach is **not safe** for:
- Multiple uvicorn workers in the same process (use `--workers 1` or run one process per tenant)
- True thread-based parallelism (GIL does not protect env mutation across threads)

For true parallel isolation without process-per-tenant overhead, the recommended future approach is context-variable-based path injection: each request carries its `brain_path` in a `contextvars.ContextVar`, eliminating shared mutable state. This is tracked in [ADR-001](adr/001-http-transport.md) as future work.

---

## Extension Points

**Adding a new tenant resolution strategy:**
Insert a new branch into the resolution algorithm at the appropriate priority position. The branch must produce a `tenant_id` string or raise HTTP 401/403; it must not mutate global state. Register the branch before the existing fallback chain.

**Adding OAuth / JWT / SAML:**
Replace or augment step 1 of the resolution algorithm. For JWT: validate signature, extract `sub` or a custom claim as `tenant_id`, check `exp`. For SAML: validate assertion at the proxy layer and forward `tenant_id` via `X-Nucleus-Tenant-ID` (step 2). No core changes required for proxy-based SSO.

**Per-tenant configuration beyond brain path:**
Add a sidecar config file at `brain_path/../nucleus_config.json` (i.e., `NUCLEUS_BRAIN_ROOT / tenant_id / nucleus_config.json`). Load it after brain path resolution and before tool dispatch. This keeps per-tenant config co-located with per-tenant data without requiring a central config store.

---

## Guarantees and Non-Guarantees

### Guarantees

- **Brain path isolation** — Every tool read and write is scoped to `NUCLEUS_BRAIN_ROOT / tenant_id / ".brain"`. No cross-tenant path access is possible through the Nucleus tool layer.
- **Token validation** — Bearer tokens are validated against `NUCLEUS_TENANT_MAP` (membership, expiry) before any tool executes. Unknown or expired tokens are rejected with HTTP 401.
- **Revocation** — Tokens listed in `NUCLEUS_REVOKED_TOKENS` are rejected immediately on every request, with no delay and no server restart required.
- **Dynamic map reload** — Tenant map and revocation list are re-read from their source (env var or file) on every request. Additions and removals take effect without restart.

### Non-Guarantees

- **Network-level isolation** — Nucleus does not enforce firewall rules, VPC segmentation, or network policies between tenants. This is the responsibility of the deployment layer (e.g., Cloud Run, Kubernetes NetworkPolicy, API gateway).
- **Rate limiting** — Nucleus does not enforce per-tenant request rate limits or quota. The deployment layer (API gateway, reverse proxy) must implement these.
- **Billing isolation** — Nucleus does not track per-tenant usage for billing purposes. Metering must be implemented in the deployment layer, upstream of Nucleus.
- **Cryptographic proof of isolation** — Brain path isolation is enforced programmatically, not by OS-level sandboxing (e.g., seccomp, namespaces, chroot). A compromised tool handler or dependency could escape the brain path. For high-assurance deployments, run one process per tenant with OS-level isolation.
- **Concurrent request safety with multiple workers** — As documented in the Concurrency Contract, multi-worker deployments are not safe with the current env-mutation approach. Use one worker per process or implement context-var injection.
