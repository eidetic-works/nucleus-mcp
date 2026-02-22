# Track 1.5: Binary Shielding (Cython)

**Status:** PROPOSED  
**Author:** Antigravity  
**Date:** January 26, 2026  
**For Review By:** Opus (Chief Architect)

---

## Executive Summary

Track 1.5 proposes **Cython compilation** of core Nucleus algorithms to protect intellectual property from bytecode extraction. This complements the Citadel Strategy by making reverse-engineering significantly harder.

---

## Problem Statement

Python's `.pyc` bytecode is trivially decompilable:

```bash
# Anyone can extract source from a wheel
pip install mcp-server-nucleus
uncompyle6 /path/to/mcp_server_nucleus/__init__.pyc > stolen_source.py
```

**Risk:** Our core algorithms (Engram Ledger, Governance Moat, Task Router) could be extracted and cloned within hours of PyPI release.

---

## Proposed Solution: Cython Shield

Cython compiles Python to C, then to native binary (`.so`/`.pyd`). This provides:

1. **Obfuscation**: No readable bytecode
2. **Performance**: 10-100x faster for compute-heavy operations
3. **Protection**: Reverse-engineering requires binary analysis expertise

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NUCLEUS PACKAGE                           │
├─────────────────────────────────────────────────────────────┤
│  PUBLIC LAYER (Pure Python - Readable)                       │
│  ├── __init__.py          # MCP tool definitions             │
│  ├── runtime/common.py    # Path utilities                   │
│  └── runtime/event_ops.py # Event emission                   │
├─────────────────────────────────────────────────────────────┤
│  PROTECTED LAYER (Cython - Binary)                           │
│  ├── _engram_core.so      # Engram write/query algorithms    │
│  ├── _governance.so       # Default-Deny enforcement         │
│  ├── _task_router.so      # Task scheduling algorithms       │
│  └── _audit_chain.so      # SHA-256 audit trail logic        │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Steps

1. **Identify Core Algorithms** (~500 lines)
   - Engram write/query with intensity sorting
   - Governance policy enforcement
   - Task priority routing
   - Audit chain hashing

2. **Create `.pyx` Files**
   ```python
   # _engram_core.pyx
   cdef class EngramEngine:
       cdef dict _ledger
       cdef int _max_intensity
       
       cpdef write(self, str key, str value, str context, int intensity):
           # Core algorithm - compiled to binary
           ...
   ```

3. **Build System**
   ```python
   # setup.py
   from Cython.Build import cythonize
   
   ext_modules = cythonize([
       "_engram_core.pyx",
       "_governance.pyx",
       "_task_router.pyx",
       "_audit_chain.pyx",
   ])
   ```

4. **Platform Wheels**
   - `mcp_server_nucleus-0.6.0-cp310-cp310-manylinux_x86_64.whl`
   - `mcp_server_nucleus-0.6.0-cp310-cp310-macosx_arm64.whl`
   - `mcp_server_nucleus-0.6.0-cp310-cp310-win_amd64.whl`

---

## Trade-offs

### Pure Python (Current v0.5.1)
| Pros | Cons |
|------|------|
| Universal wheel | Trivially decompilable |
| Easy debugging | No performance gains |
| Simple CI/CD | IP exposure risk |

### Cython Shield (Proposed v0.6.0)
| Pros | Cons |
|------|------|
| Binary protection | Platform-specific wheels |
| 10-100x faster | Complex build matrix |
| Harder to clone | Debugging complexity |

---

## Effort Estimate

| Task | Hours | Complexity |
|------|-------|------------|
| Identify core algorithms | 2 | Low |
| Create .pyx files | 8 | Medium |
| Build system setup | 4 | Medium |
| Multi-platform CI | 8 | High |
| Testing | 4 | Medium |
| **Total** | **26** | Medium-High |

---

## Recommendation

**For v0.5.1:** Ship pure Python for rapid iteration and beta feedback.

**For v0.6.0:** Implement Cython Shield for production hardening.

**For v1.0.0:** Consider Rust rewrite for ultimate sovereignty (per Citadel Strategy).

---

## Alternatives Considered

### 1. PyArmor
- Commercial obfuscator
- Adds ~$500/year cost
- Still Python bytecode (weaker protection)

### 2. Nuitka
- Full Python-to-C compiler
- Larger binary size
- More complex debugging

### 3. Rust Migration (Track 2.0)
- Ultimate protection
- Highest effort (months)
- Best long-term choice

---

## Architect Decision Required

Opus, please evaluate:

1. **Defer to v0.6.0?** (Focus on market validation first)
2. **Prioritize for v0.5.2?** (Protect before scale)
3. **Skip Cython, go direct to Rust?** (Long-term play)

---

## Security Note

Even with Cython, a determined attacker can:
- Use binary analysis tools (IDA Pro, Ghidra)
- Intercept MCP protocol messages
- Reverse-engineer through observation

Cython raises the bar significantly but is not absolute protection. The Citadel Strategy (private source + selective access) remains the primary defense.

---

*Document prepared by Antigravity, January 26, 2026*
