# Nucleus Telemetry

Nucleus collects **anonymous, aggregate usage statistics** to help us understand how the tool is used and improve it. This page explains exactly what is collected, what is never collected, and how to opt out.

## TL;DR

- **Enabled by default** (opt-out model, industry standard)
- **Opt out in 1 command:** `nucleus config --no-telemetry`
- **What we collect:** command name, duration, error type, Nucleus version, Python version, OS
- **What we NEVER collect:** your data, engram content, file paths, prompts, API keys

---

## What Is Collected

When you run a Nucleus command (CLI or MCP), the following anonymous data is sent:

| Field | Example | Why |
|-------|---------|-----|
| Command name | `morning-brief`, `engram.write` | Know which features are used |
| Tool category | `cli`, `nucleus_engrams` | Understand usage patterns |
| Duration (ms) | `150.3` | Find performance bottlenecks |
| Error type | `ValueError` (class name only) | Fix common errors |
| Nucleus version | `1.5.0` | Track adoption of releases |
| Python version | `3.12.1` | Know which Python versions to support |
| OS platform | `darwin`, `linux` | Prioritize platform support |
| OS architecture | `arm64`, `x86_64` | Optimize for common hardware |

**That's it.** Nothing else.

---

## What Is NEVER Collected

We take privacy seriously. The following is **never** sent:

- ❌ Engram content or keys
- ❌ File paths or directory names
- ❌ Organization documents or notes
- ❌ Prompts, LLM responses, or conversation content
- ❌ API keys, tokens, or credentials
- ❌ User names, emails, or any PII
- ❌ IP addresses (not logged server-side)
- ❌ Device IDs, cookies, or tracking identifiers
- ❌ Git history, commit messages, or code

---

## How It Works

Nucleus uses [OpenTelemetry](https://opentelemetry.io/) to send anonymous data to `telemetry.nucleusos.dev`. The telemetry pipeline is **completely separate** from any enterprise OTel configuration you may have — it uses its own TracerProvider and MeterProvider with zero interference.

The telemetry is **fire-and-forget**: if the endpoint is unreachable, Nucleus silently continues with zero impact on your workflow.

### Architecture

```
Your Nucleus installation
    │
    │  OTLP gRPC (anonymous data only)
    ▼
telemetry.nucleusos.dev
    │
    ▼
Aggregate dashboards (no individual tracking)
```

---

## How to Opt Out

### Option 1: CLI Command (recommended)
```bash
nucleus config --no-telemetry
```

### Option 2: Environment Variable
```bash
export NUCLEUS_ANON_TELEMETRY=false
```

### Option 3: Edit Config File
Edit `.brain/config/nucleus.yaml`:
```yaml
telemetry:
  anonymous:
    enabled: false
```

### To Re-Enable
```bash
nucleus config --telemetry
```

---

## First-Run Notice

On first use, Nucleus displays a one-time notice:

```
ℹ️  Nucleus collects anonymous usage stats to improve the product.
   No personal data, no engram content, no org docs. Ever.
   To opt out: nucleus config --no-telemetry
```

This notice appears once and is never shown again.

---

## Why We Collect Telemetry

As an open-source project, we have no other way to understand:

1. **Which features matter** — Should we invest in engrams or federation?
2. **Where users struggle** — Which commands fail most often?
3. **Platform priorities** — Should we focus on macOS or Linux?
4. **Version adoption** — Are users upgrading?
5. **Performance** — Are commands getting slower over releases?

This data directly shapes our roadmap and helps us build a better tool for you.

---

## Comparison with Other Tools

Our telemetry follows the same opt-out model used by:

| Tool | Telemetry Model | Opt-Out |
|------|----------------|---------|
| VS Code | Opt-out | Settings toggle |
| Homebrew | Opt-out | `HOMEBREW_NO_ANALYTICS=1` |
| npm | Opt-out | `npm config set fund false` |
| Next.js | Opt-out | `npx next telemetry disable` |
| **Nucleus** | **Opt-out** | **`nucleus config --no-telemetry`** |

---

## Source Code

The telemetry implementation is fully open source:

- **Client:** [`runtime/anon_telemetry.py`](src/mcp_server_nucleus/runtime/anon_telemetry.py)
- **Server:** [`infra/telemetry/`](infra/telemetry/)
- **Tests:** [`tests/test_anon_telemetry.py`](tests/test_anon_telemetry.py)

You can audit every line of code that sends telemetry data.

---

## Questions?

- **Email:** [hello@nucleusos.dev](mailto:hello@nucleusos.dev)
- **Discord:** [Join our server](https://discord.gg/RJuBNNJ5MT)
- **GitHub:** [Open an issue](https://github.com/eidetic-works/nucleus-mcp/issues)
