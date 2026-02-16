# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Yes             |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

**Do NOT report security vulnerabilities via public GitHub Issues.**

### How to Report

1. **Email**: security@nucleusos.dev
2. **Subject**: `[SECURITY] Brief description`
3. **Include**:
   - Detailed description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Varies by severity
  - Critical: 24-72 hours
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next release cycle

### Responsible Disclosure

We follow responsible disclosure practices:

1. We will acknowledge your report within 48 hours
2. We will provide an estimated timeline for the fix
3. We will notify you when the vulnerability is fixed
4. We will credit you in the release notes (unless you prefer anonymity)

## Security Best Practices

### For Users

1. **Keep Nucleus Updated**: Always use the latest version
2. **Protect Your `.brain/` Folder**: Contains your project context
3. **Review Audit Logs**: Check `events.jsonl` for suspicious activity
4. **Use File Locking**: Lock critical files during sensitive operations

### For Contributors

1. **No Hardcoded Secrets**: Never commit API keys, tokens, or credentials
2. **Input Validation**: Validate all user inputs
3. **Path Traversal**: Prevent directory traversal attacks
4. **Dependency Auditing**: Keep dependencies updated

## Security Features

Nucleus includes several security features:

- **Local-First Architecture**: Your data never leaves your machine
- **Audit Trail**: Every action logged to `events.jsonl`
- **File Locking**: Hypervisor-level immutable locks
- **Intent-Aware Metadata**: Know WHO locked WHAT and WHY

## Known Security Considerations

### MCP Protocol

Nucleus operates as an MCP server. Be aware that:

- MCP clients (Claude, Cursor, etc.) have full access to exposed tools
- Environment variables may contain sensitive paths
- The `.brain/` folder should be treated as sensitive data

### Multi-Agent Sync

When using multi-agent sync:

- All agents with access to `.brain/` can read/write data
- Sync conflicts are resolved via last-write-wins by default
- Consider file locking for critical operations

---

*Security is a shared responsibility. Thank you for helping keep Nucleus safe.*
