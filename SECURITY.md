# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.6.x   | ✅ Active support  |
| 1.5.x   | ⚠️ Security fixes only |
| < 1.5   | ❌ No longer supported |

## Reporting a Vulnerability

**Do NOT report security vulnerabilities via public GitHub Issues.**

### Private Disclosure

Email: **security@nucleusos.dev**

Until the email is active, please use GitHub's private vulnerability reporting:
1. Go to the repository's Security tab
2. Click "Report a vulnerability"
3. Follow the private disclosure process

### What to Include

- **Description**: Clear explanation of the vulnerability
- **Impact**: What can an attacker do with this?
- **Steps to Reproduce**: Minimal example to trigger the issue
- **Environment**: Python version, OS, MCP client
- **Suggested Fix**: If you have one (optional)

### Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgment | 48 hours |
| Initial Assessment | 7 days |
| Fix Development | 14-30 days |
| Public Disclosure | After fix released |

### Scope

In scope:
- Authentication/authorization bypasses
- Default-Deny policy circumvention
- Audit trail tampering
- Information disclosure
- Remote code execution
- Denial of service

Out of scope:
- Social engineering
- Physical attacks
- Issues in dependencies (report upstream)
- Issues requiring local access (by design)

## Security Architecture

### Default-Deny

Nucleus enforces **Default-Deny** at the runtime level:

```
┌─────────────────────────────────────────┐
│         MCP TOOL REQUEST                │
├─────────────────────────────────────────┤
│  ↓                                      │
│  Policy Check (Default: DENY)           │
│  ↓                                      │
│  [ALLOW?] → Execute Tool                │
│  [DENY?]  → Log + Block                 │
└─────────────────────────────────────────┘
```

### Cryptographic Audit

Every interaction is logged with SHA-256 hashing:

```json
{
  "timestamp": "2026-01-26T20:00:00Z",
  "action": "tool_call",
  "tool": "brain_write_engram",
  "params_hash": "sha256:abc123...",
  "result_hash": "sha256:def456...",
  "prev_hash": "sha256:789xyz..."
}
```

The hash chain makes tampering detectable.

### Data Storage

- All data stored locally in `.brain/` directory
- No external data transmission by default
- User controls all persistence

## Security Best Practices

### For Users

1. **Protect your `.brain/` directory**
   - Don't commit to public repos
   - Use `.gitignore` to exclude it
   - Backup sensitive engrams

2. **Review mounted servers**
   - Only mount trusted MCP servers
   - Audit `brain_list_mounted()` regularly

3. **Monitor audit logs**
   - Check `brain_audit_log()` periodically
   - Look for unexpected tool calls

### For Administrators

1. **Use environment isolation**
   - Separate `.brain/` per project
   - Use containers for untrusted agents

2. **Restrict file access**
   - Set appropriate permissions on `.brain/`
   - Consider read-only mounts for sensitive data

3. **Enable logging**
   - Keep `interaction_log.jsonl` for forensics
   - Archive logs securely

## Known Security Considerations

### Bytecode Extraction

Python bytecode can be decompiled. We address this via:
- Runtime-only secret management (no secrets in source)
- Planned: Cython compilation for performance-critical paths
- Planned: Rust migration for core modules

### MCP Protocol

MCP messages are not encrypted by default. For sensitive deployments:
- Use localhost connections only
- Implement TLS for remote connections
- Consider network isolation

### Engram Sensitivity

Engrams may contain sensitive information. Users should:
- Avoid storing secrets in engrams
- Use external secret managers
- Encrypt sensitive engram values

### npm-wrapper subprocess invocations

`npm-wrapper/index.js` is the npx entrypoint that bridges npm distribution to
the Python package. It uses `child_process` because that is the only way to
launch a separate process from Node — equivalent to how an npm package with
native dependencies invokes `node-gyp` at install time. Static security
scanners (e.g. SafeSkill) flag every `child_process` call site as critical
without flow analysis; the table below is the per-call rationale.

| Line | Call | Bounded by |
|---|---|---|
| `index.js:14` | `execSync('python3 --version', { stdio: 'ignore' })` | Hardcoded literal command. No user-input concatenation. `stdio: 'ignore'` discards output. |
| `index.js:23` | `execSync('python3 -m mcp_server_nucleus --help', { stdio: 'ignore' })` | Hardcoded literal command. No user-input concatenation. `stdio: 'ignore'` discards output. |
| `index.js:33` | `execSync('python3 -m pip install nucleus-mcp', { stdio: 'inherit' })` | Hardcoded literal command + hardcoded package name. No user-input concatenation. `stdio: 'inherit'` only streams pip's own output to the user terminal. By-design behavior of an npm wrapper over a Python package. |
| `index.js:65` | `spawn('python3', pythonArgs, { stdio: 'inherit', shell: false })` | `shell: false` — argv passed as a discrete array, no shell interpretation, no shell-injection vector. User-supplied CLI args ARE forwarded into the Python process as argv entries; they are parsed by the Python CLI's `argparse`, not by a shell. Any vulnerability in argv handling belongs to the Python package, not this wrapper. Defense-in-depth: `validateArgs()` rejects argv entries containing null bytes before spawn. |

The wrapper does not:
- Concatenate user input into any shell command string.
- Use `child_process.exec()` (which spawns a shell). Only `execSync` (with hardcoded literals) and `spawn` (with `shell: false`) are used.
- Read environment variables that flow into a command string.
- Execute any binary other than `python3`.

False-positive reports for SafeSkill and other static scanners on these call
sites should reference this section.

## Acknowledgments

We thank the following researchers for responsible disclosure:

*(No vulnerabilities reported yet)*

---

*Security policy maintained by the Nucleus team.*
*Last updated: January 26, 2026*
