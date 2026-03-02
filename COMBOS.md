# God Combos — Multi-Tool Automation Pipelines

**Version:** 1.2.0 | **Facade:** `nucleus_engrams` | **Module:** `runtime/god_combos/`

God Combos are composable automation pipelines that chain multiple Nucleus facade actions into a single invocation. Each combo:
- Accepts a trigger (manual or automated)
- Chains internal Python calls (no MCP round-trip overhead)
- Returns a structured report
- Writes an engram for persistent memory
- Has a circuit breaker (max iterations / cost cap)

---

## 1. Pulse & Polish

**Action:** `pulse_and_polish`  
**Pipeline:** `prometheus_metrics` → `audit_log` → `morning_brief` → `write_engram`  
**Use case:** Automated Chief of Staff — daily health check and synthesis.

```
nucleus_engrams(action="pulse_and_polish", params={"write_engram": true})
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `write_engram` | bool | `true` | Write synthesis engram to memory |

**Returns:** `{ pipeline_steps, health_classification, synthesis_engram, circuit_breaker_status }`

**File:** `runtime/god_combos/pulse_and_polish.py`

---

## 2. Self-Healing SRE

**Action:** `self_healing_sre`  
**Pipeline:** `search_engrams` → `performance_metrics` → diagnose → recommend  
**Use case:** SRE diagnosis — given a symptom, searches memory for prior incidents, checks current metrics, classifies severity, and recommends action.

```
nucleus_engrams(action="self_healing_sre", params={"symptom": "high latency on /api/v1"})
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symptom` | str | *required* | The symptom or issue to diagnose |
| `write_engram` | bool | `true` | Write diagnosis engram to memory |

**Returns:** `{ symptom, prior_incidents, current_metrics, severity, recommendation, engram_written }`

**Severity levels:** `critical` (≥3 priors + degraded metrics), `warning` (1-2 priors or some degradation), `info` (no prior incidents, metrics OK)

**File:** `runtime/god_combos/self_healing_sre.py`

---

## 3. Fusion Reactor

**Action:** `fusion_reactor`  
**Pipeline:** capture → recall → synthesize → compound  
**Use case:** Self-reinforcing memory loop — turns a single observation into compounded knowledge by linking it to existing engrams and creating a synthesis.

```
nucleus_engrams(action="fusion_reactor", params={
    "observation": "Users prefer dark mode by 3:1 ratio",
    "context": "Feature",
    "intensity": 7
})
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `observation` | str | *required* | The observation to capture and compound |
| `context` | str | `"Decision"` | Engram context (Feature, Architecture, Brand, Strategy, Decision) |
| `intensity` | int | `6` | Base intensity (1-10, capped at 10 after compounding) |
| `write_engrams` | bool | `true` | Write capture + synthesis engrams |

**Returns:** `{ capture, recall, synthesis, compound_factor, pipeline }`

**Compounding:** Synthesis intensity = `min(base + 1, 10)`. Compound factor = `len(related_engrams) + 1`.

**File:** `runtime/god_combos/fusion_reactor.py`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                nucleus_engrams                   │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ pulse_and_  │ │ self_healing_│ │  fusion_   │ │
│  │   polish    │ │    sre       │ │  reactor   │ │
│  └──────┬──────┘ └──────┬───────┘ └─────┬─────┘ │
│         │               │               │       │
│  ┌──────▼──────────────▼───────────────▼─────┐ │
│  │         Internal Python Imports            │ │
│  │   (no MCP overhead, direct function call)  │ │
│  └──────┬──────────────┬───────────────┬─────┘ │
│         │               │               │       │
│  ┌──────▼──┐ ┌─────────▼──┐ ┌─────────▼──┐    │
│  │engram_  │ │performance_│ │prometheus_ │    │
│  │  ops    │ │  metrics   │ │  metrics   │    │
│  └─────────┘ └────────────┘ └────────────┘    │
└─────────────────────────────────────────────────┘
```

## Adding a New God Combo

1. Create `runtime/god_combos/your_combo.py` with a `run_your_combo(**kwargs) -> dict` function
2. Add a handler in `tools/engrams.py`:
   ```python
   def _h_your_combo(**params):
       from ..runtime.god_combos.your_combo import run_your_combo
       return make_response(True, data=run_your_combo(**params))
   ```
3. Add to `ROUTER` dict and docstring in `tools/engrams.py`
4. Add tests in `tests/test_god_combos.py`
5. Update this document

## Test Coverage

All combos are tested in `tests/test_god_combos.py`:
- Pipeline success paths
- Circuit breaker behavior
- Engram writing verification
- Severity/intensity classification
- Dry-run mode (`write_engram=false`)
