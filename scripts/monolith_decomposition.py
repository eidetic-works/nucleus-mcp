"""
Monolith Decomposition Script
Automates migration of code from __init__.py to modular structure
"""

import os
import re
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "mcp_server_nucleus"
MONOLITH_PATH = SRC_DIR / "__init__.py"

# Migration groups with start/end markers
MIGRATION_GROUPS = [
    {
        "name": "core_tool_registration",
        "start_marker": "# =============================================================================\n# v0.6.0 PROTOCOL COUPLING FIX - Tiered Tool Registration\n# =============================================================================",
        "end_marker": "# ============================================================",
        "target_module": "core/tool_registration_impl.py"
    },
    {
        "name": "orchestrator_init",
        "start_marker": "# ============================================================\n# ORCHESTRATOR V3.1 INTEGRATION",
        "end_marker": "# ============================================================",
        "target_module": "core/orchestrator.py"
    },
    {
        "name": "deployment_management",
        "start_marker": "# ============================================================\n# RENDER POLLER (Deploy monitoring)",
        "end_marker": "# ============================================================\n# FEATURE MAP (Product feature inventory)",
        "target_module": "deployment/render_integration.py",
        "context_before": 5,
        "context_after": 5
    },
    {
        "name": "deployment_management_fallback",
        "start_line": 350,
        "end_line": 550,
        "target_module": "deployment/render_integration_fallback.py"
    }
]

def extract_code_section(content, start_marker, end_marker, context_before=0, context_after=0):
    """Extract code section with context lines"""
    start_idx = content.find(start_marker)
    if start_idx == -1:
        return None
        
    end_idx = content.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1:
        return None
        
    # Expand selection with context
    start_line_idx = content.rfind('\n', 0, start_idx) + 1
    for _ in range(context_before):
        start_line_idx = content.rfind('\n', 0, start_line_idx - 1) + 1
        
    end_line_end = content.find('\n', end_idx + len(end_marker))
    for _ in range(context_after):
        next_newline = content.find('\n', end_line_end + 1)
        if next_newline != -1:
            end_line_end = next_newline
        
    return content[start_line_idx:end_line_end]

def extract_by_line_numbers(content, start_line, end_line):
    """Extract code section by line numbers"""
    lines = content.split('\n')
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return None
    return "\n".join(lines[start_line-1:end_line])

def migrate_code():
    """Main migration function"""
    # Read monolith content
    with open(MONOLITH_PATH, "r") as f:
        monolith_content = f.read()
    
    # Process each migration group
    for group in MIGRATION_GROUPS:
        if "start_marker" in group:
            section = extract_code_section(
                monolith_content,
                group["start_marker"],
                group["end_marker"],
                group.get("context_before", 0),
                group.get("context_after", 0)
            )
        elif "start_line" in group:
            section = extract_by_line_numbers(
                monolith_content,
                group["start_line"],
                group["end_line"]
            )
        
        if section:
            # Create target module
            target_path = SRC_DIR / group["target_module"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write extracted code to new module
            with open(target_path, "w") as f:
                f.write(f"""# Auto-generated from monolith decomposition\n""")
                f.write(section)
                
            # Remove section from monolith
            if "start_marker" in group:
                monolith_content = monolith_content.replace(section, "")
            else:
                print(f"Section not removed from monolith for {group['name']}")
                
            print(f"Migrated {group['name']} to {target_path}")
        else:
            if "start_marker" in group:
                print(f"Section not found for {group['name']}")
            else:
                print(f"Section not found for {group['name']} at lines {group['start_line']}-{group['end_line']}")
    
    # Write updated monolith
    with open(MONOLITH_PATH, "w") as f:
        f.write(monolith_content)
    
    print("Monolith decomposition complete!")

if __name__ == "__main__":
    migrate_code()
