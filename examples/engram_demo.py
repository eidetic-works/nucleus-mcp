#!/usr/bin/env python3
"""
Engram Ledger Demo

Demonstrates the Engram Ledger - Nucleus's persistent memory system.
Engrams are memory units with intensity scoring that survive across sessions.
"""

import os
from pathlib import Path

# Setup test environment
TEST_BRAIN = Path("/tmp/nucleus_engram_demo")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

def main():
    print("=" * 60)
    print("ENGRAM LEDGER DEMO")
    print("=" * 60)
    
    print("""
The Engram Ledger is Nucleus's persistent memory system.

WHAT IS AN ENGRAM?
------------------
An Engram is a memory unit with:
- Key: Unique identifier (e.g., "auth_decision")
- Value: The memory content (should include reasoning)
- Context: Category (Feature, Architecture, Brand, Strategy, Decision)
- Intensity: 1-10 priority (10 = critical, must never forget)

CONTEXT CATEGORIES
------------------
| Context      | Use For                                |
|--------------|----------------------------------------|
| Feature      | Product features and capabilities      |
| Architecture | Technical decisions and patterns       |
| Brand        | Brand guidelines and positioning       |
| Strategy     | Business strategy and roadmap          |
| Decision     | Key decisions with reasoning           |

INTENSITY SCALE
---------------
| Level | Meaning                    | Example                      |
|-------|----------------------------|------------------------------|
| 10    | Critical constraint        | "Never use OpenAI"           |
| 8-9   | Important decision         | "Use PostgreSQL for ACID"    |
| 5-7   | Standard memory            | "Prefer TypeScript"          |
| 3-4   | Nice to remember           | "User likes dark mode"       |
| 1-2   | Archive/historical         | "Tried Redis, switched"      |

EXAMPLE USAGE
-------------

# Write a critical constraint
brain_write_engram(
    key="no_openai",
    value="Budget constraint - use Gemini only because cost",
    context="Decision",
    intensity=10
)

# Write an architectural decision
brain_write_engram(
    key="db_choice",
    value="PostgreSQL for ACID compliance - needed for financial data",
    context="Architecture",
    intensity=8
)

# Query all Architecture engrams with high intensity
brain_query_engrams(
    context="Architecture",
    min_intensity=7
)
# Returns engrams sorted by intensity (highest first)

# Query all engrams across all contexts
brain_query_engrams(min_intensity=5)

WHY ENGRAMS MATTER
------------------
1. Survive session boundaries (unlike chat context)
2. Agents can recall critical constraints
3. Prevents "amnesia" between conversations
4. Creates institutional memory for projects

GOVERNANCE INTEGRATION
----------------------
brain_governance_status() includes:
- Total engram count
- Engrams by context
- High-intensity constraint alerts
""")

    print("=" * 60)
    print("Try these commands in your MCP client:")
    print("  brain_write_engram(...)")
    print("  brain_query_engrams(...)")
    print("  brain_governance_status()")
    print("=" * 60)

if __name__ == "__main__":
    main()
