# Release Checklist — v1.5.1 "The Transparent Brain"

## What YOU (Founder) Need to Do on nucleusos.dev Before Public Release

Everything below is ordered by priority. Steps 1-4 are **BLOCKING** — telemetry will silently fail without them (which is fine for users, but you get no data). Steps 5+ are recommended but not blocking.

---

## 🔴 BLOCKING (Must Do Before Release)

### 1. DNS Record (5 minutes)

Go to your DNS provider for `nucleusos.dev` and add:

```
Type: A
Name: telemetry
Value: <YOUR_VPS_IP>
TTL: 300
```

**Where to do this:** Wherever you manage `nucleusos.dev` DNS (Cloudflare, Namecheap, Google Domains, etc.)

**Verify:**
```bash
dig telemetry.nucleusos.dev +short
# Should return your VPS IP
```

### 2. Provision a VPS (10 minutes)

**Cheapest option that works:** $5/mo VPS from Hetzner, DigitalOcean, or Vultr.

Requirements:
- 1 vCPU, 1GB RAM, 10GB disk
- Ubuntu 22.04 or Debian 12
- Docker + Docker Compose installed

```bash
# Quick Docker install on Ubuntu:
ssh root@<VPS_IP>
curl -fsSL https://get.docker.com | sh
```

### 3. Deploy the Collector Stack (5 minutes)

From your local machine:

```bash
cd mcp-server-nucleus/infra/telemetry
./deploy.sh root@<VPS_IP>
```

Or manually:
```bash
scp -r infra/telemetry/* root@<VPS_IP>:/opt/nucleus-telemetry/
ssh root@<VPS_IP> "cd /opt/nucleus-telemetry && docker compose up -d"
```

### 4. Verify End-to-End (2 minutes)

```bash
# On your local machine:
NUCLEUS_ANON_TELEMETRY=true nucleus morning-brief

# On the VPS:
docker logs nucleus-otel-collector --tail 10
# Should show received spans/metrics

# Grafana:
open https://telemetry.nucleusos.dev:3000
# Login: admin/admin → CHANGE PASSWORD IMMEDIATELY
```

---

## 🟡 RECOMMENDED (Before or Shortly After Release)

### 5. Firewall Rules (2 minutes)

```bash
ssh root@<VPS_IP>
ufw allow 4317/tcp          # OTLP gRPC ingest (from Nucleus clients)
ufw allow 80/tcp             # Caddy HTTP→HTTPS redirect
ufw allow 443/tcp            # Caddy TLS
ufw allow from <YOUR_IP> to any port 3000  # Grafana (RESTRICT!)
ufw deny 9090/tcp            # Block direct Prometheus access
ufw enable
```

### 6. Change Grafana Password

```bash
open https://telemetry.nucleusos.dev:3000
# Login: admin / admin
# Change to a strong password
```

### 7. Bump Version in pyproject.toml

```bash
# In pyproject.toml, change:
version = "1.3.1"
# To:
version = "1.5.1"
```

### 8. Publish to PyPI

```bash
cd mcp-server-nucleus
pip install build twine
python -m build
twine upload dist/nucleus_mcp-1.5.1*
```

### 9. Git Tag + Push

```bash
git add -A
git commit -m "v1.5.1: Anonymous opt-out telemetry

- Separate OTel pipeline for anonymous usage data
- nucleus config --no-telemetry to opt out
- First-run notice with opt-out instructions
- Server-side collector stack (Docker Compose)
- TELEMETRY.md transparency page
- 23 new tests, 87 total regression passing"

git tag v1.5.1
git push origin main --tags
```

### 10. GitHub Release

Create a release at https://github.com/eidetic-works/nucleus-mcp/releases/new

- Tag: `v1.5.1`
- Title: `v1.5.1 — "The Transparent Brain"`
- Body: Copy from CHANGELOG.md

---

## 🟢 NICE TO HAVE (Post-Release)

### 11. Add Telemetry Page to nucleusos.dev Website

Copy `TELEMETRY.md` content to a `/telemetry` page on your website. This builds trust with privacy-conscious users.

### 12. Update HUD Dashboard

If `hud.nucleusos.dev` has a tool catalog, add `nucleus config` to it.

### 13. Monitor First 24 Hours

```bash
# Check collector is receiving data:
ssh root@<VPS_IP> "docker logs nucleus-otel-collector --tail 50"

# Check Prometheus has metrics:
curl "http://<VPS_IP>:9090/api/v1/query?query=nucleus_nucleus_anon_commands_total"

# Check Grafana dashboard:
open https://telemetry.nucleusos.dev:3000/d/nucleus-anon-usage
```

### 14. Set Up Alerts (Optional)

In Grafana, create alerts for:
- Collector health check failing
- Zero ingested spans for >1 hour (means no one is using Nucleus, or collector is broken)
- Disk usage >80% on telemetry volume

---

## Quick Reference: What's Already Done (Code-Side)

| Component | Status | Files |
|-----------|--------|-------|
| Anonymous telemetry module | ✅ | `runtime/anon_telemetry.py` |
| CLI hooks (success + error) | ✅ | `cli.py` |
| MCP dispatch hooks (6 points) | ✅ | `tools/_dispatch.py` |
| `nucleus config` command | ✅ | `cli.py` |
| First-run notice | ✅ | `runtime/anon_telemetry.py` |
| Brain init seeds config | ✅ | `cli.py` |
| Unit tests (23/23) | ✅ | `tests/test_anon_telemetry.py` |
| Regression tests (87/87) | ✅ | All test files |
| OTel Collector config | ✅ | `infra/telemetry/` |
| Docker Compose stack | ✅ | `infra/telemetry/docker-compose.yaml` |
| Grafana dashboard | ✅ | `infra/telemetry/grafana/` |
| Deploy script | ✅ | `infra/telemetry/deploy.sh` |
| TELEMETRY.md | ✅ | Root of repo |
| README.md updated | ✅ | Root of repo |
| CHANGELOG.md updated | ✅ | Root of repo |

---

## Cost Summary

| Resource | Monthly Cost |
|----------|-------------|
| VPS (1vCPU/1GB) | $5 |
| DNS (included) | $0 |
| TLS (Let's Encrypt) | $0 |
| **Total** | **$5/mo** |

Handles thousands of Nucleus installs. Scale up only if you hit 10k+ active users.
