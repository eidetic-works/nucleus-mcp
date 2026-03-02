# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | ✅ Active support  |
| 0.4.x   | ⚠️ Security fixes only |
| < 0.4   | ❌ No longer supported |

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
- Citadel Strategy (private source)
- Track 1.5: Cython compilation (planned)
- Track 2.0: Rust migration (roadmap)

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

## Acknowledgments

We thank the following researchers for responsible disclosure:

*(No vulnerabilities reported yet)*

---

*Security policy maintained by the Nucleus team.*
*Last updated: January 26, 2026*
