#!/bin/bash

# demo_governance.sh - Nucleus MCP Security Flow Demo
# This script demonstrates the core security features: Init, Engram Write, Query, and Audit Log.

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Nucleus MCP: Sovereign Security Demo ===${NC}"
echo -e "${BLUE}Initializing Sovereign Control Plane...${NC}"

# 1. Initialize (Scan mode)
echo -e "${GREEN}> nucleus-init --scan${NC}"
# Simulating the init output for the demo
echo "Scanning for AI tool configurations..."
echo "✅ Claude Desktop detected"
echo "✅ Cursor detected"
echo "✅ Windsurf detected"
echo "Creating .brain/ ledger..."
echo -e "${GREEN}Sovereign Control Plane ready.${NC}\n"

# 2. Write Engram (Memory)
echo -e "${BLUE}Storing a sensitive architectural decision (Engram)...${NC}"
echo -e "${GREEN}> nucleus-write \"Use local-first SQLite for the policy engine to avoid cloud dependency.\"${NC}"
echo -e "✅ Engram encrypted and stored in .brain/ledger.jsonl\n"

# 3. Query Engram
echo -e "${BLUE}Retrieving context with a query...${NC}"
echo -e "${GREEN}> nucleus-query \"policy engine storage\"${NC}"
echo -e "🧠 Found 1 engram (Intensity 98%):"
echo -e "   - \"Use local-first SQLite for the policy engine to avoid cloud dependency.\"\n"

# 4. Audit Log (The "Who/When/Why")
echo -e "${BLUE}Inspecting the tamper-proof Audit Log...${NC}"
echo -e "${GREEN}> nucleus-audit --last 5${NC}"
echo -e "| Timestamp | Agent ID | Action | Resource | Reason |"
echo -e "|-----------|----------|--------|----------|--------|"
echo -e "| 15:35:01  | manual   | write  | engram   | User choice |"
echo -e "| 15:35:10  | manual   | query  | engram   | Context retrieval |"
echo -e "\n${BLUE}=== Demo Complete: 100% Local. 100% Audited. ===${NC}"
