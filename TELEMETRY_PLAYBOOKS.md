# Telemetry Playbooks — "If X Breaks, Check Y"

Debugging flows for the Nucleus telemetry pipeline. Written for both humans and LLMs.

> Architecture docs: `WINDSURF_SUPER_PROMPT.md` (Phase C3)

---

## Playbook 1: No Spans Showing in Summary

**Symptom:** `npm run telemetry:summary` shows `Total spans: 0`

**Diagnosis flow:**

1. **Is the collector running?**
   ```bash
   docker ps | grep nucleus-otel-collector
   ```
   - If not: `npm run telemetry:up`

2. **Did you run a command with telemetry enabled?**
   ```bash
   NUCLEUS_ANON_TELEMETRY=true nucleus morning-brief
   ```

3. **Is the drain script running?**
   - Check for the terminal running `npm run telemetry:drain`
   - If not: start it in a new terminal

4. **Are there spans in Upstash?**
   ```bash
   curl "${UPSTASH_REDIS_REST_URL}/llen/nucleus:spans" \
     -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"
   ```
   - If count > 0: drain is not forwarding. Check drain logs.
   - If count = 0: spans aren't reaching Upstash. Check Worker.

5. **Full audit:**
   ```bash
   npm run telemetry:audit
   ```

---

## Playbook 2: Drain Script Errors

**Symptom:** Drain terminal shows `❌ Error forwarding span`

**Diagnosis flow:**

1. **Is collector accepting HTTP OTLP?**
   ```bash
   curl -X POST http://localhost:4318/v1/traces \
     -H "Content-Type: application/x-protobuf" \
     --data-binary @/dev/null
   ```
   - Should return 200 or 400 (not connection refused)

2. **Check port mapping:**
   ```bash
   docker port nucleus-otel-collector
   ```
   - Should show `4317/tcp -> 0.0.0.0:4317` and `4318/tcp -> 0.0.0.0:4318`

3. **Base64 encoding mismatch?**
   - Worker encodes with `btoa(String.fromCharCode(...new Uint8Array(body)))`
   - Drain decodes with `Buffer.from(entry, 'base64')`
   - These should be symmetric. If you changed one, update the other.

---

## Playbook 3: Cloudflare Worker Returns 500

**Symptom:** Worker logs show `failed to queue` or `Upstash env vars not set`

**Diagnosis flow:**

1. **Check Worker env vars in Cloudflare dashboard:**
   - `UPSTASH_REDIS_REST_URL` — must be the REST URL (https://...), not Redis TCP URL
   - `UPSTASH_REDIS_REST_TOKEN` — must be the REST token, not Redis password

2. **Test Upstash REST directly:**
   ```bash
   curl "${UPSTASH_REDIS_REST_URL}/ping" \
     -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"
   ```
   - Should return `{"result":"PONG"}`

3. **Redeploy Worker:**
   - Cloudflare dashboard → Workers & Pages → nucleus-telemetry → Quick Edit → Deploy

---

## Playbook 4: Tunnel Not Working

**Symptom:** Worker's direct send to `telemetry.nucleusos.dev` always fails, falls back to Upstash

**Diagnosis flow:**

1. **Is cloudflared running?**
   ```bash
   pgrep -f "cloudflared.*tunnel"
   ```

2. **Start tunnel:**
   ```bash
   cloudflared tunnel run nucleus-telemetry
   ```

3. **DNS check:**
   ```bash
   dig telemetry.nucleusos.dev +short
   ```
   - Should return a Cloudflare IP or your VPS IP

4. **Direct test:**
   ```bash
   curl -X POST https://telemetry.nucleusos.dev/v1/traces \
     -H "Content-Type: application/x-protobuf" \
     --data-binary @/dev/null
   ```

---

## Playbook 5: High Error Rate in Grafana

**Symptom:** Error rate panel shows > 5%

**Diagnosis flow:**

1. **Run brief for details:**
   ```bash
   npm run telemetry:brief
   ```

2. **Check top error types in Grafana:**
   - Dashboard: `nucleus-anon-usage` → "Top Error Types" panel

3. **Automated diagnosis:**
   ```bash
   nucleus combo diagnose "high telemetry error rate"
   ```

4. **Manual log check:**
   ```bash
   docker logs nucleus-otel-collector --tail 200 | grep -i error
   ```

---

## Playbook 6: Collector Keeps Restarting

**Symptom:** `docker ps` shows collector with high restart count

**Diagnosis flow:**

1. **Check OOM or config errors:**
   ```bash
   docker logs nucleus-otel-collector 2>&1 | head -50
   ```

2. **Common causes:**
   - Memory limit too low → increase in docker-compose.yaml
   - Bad config YAML → validate with `otelcol validate --config=...`
   - Port conflict → check if another process uses 4317/4318

3. **Restart clean:**
   ```bash
   npm run telemetry:down
   docker rm nucleus-otel-collector
   npm run telemetry:up
   ```

---

## Quick Reference: Complete Health Check

Run this sequence to verify the entire pipeline:

```bash
# 1. Audit config
npm run telemetry:audit

# 2. Start everything
npm run telemetry:all

# 3. Generate a test span
NUCLEUS_ANON_TELEMETRY=true nucleus morning-brief

# 4. Check summary
npm run telemetry:summary

# 5. Generate brief
npm run telemetry:brief
```

If all 5 commands succeed and summary shows > 0 spans, the pipeline is healthy.

---

*Keep this file updated when telemetry components change.*
