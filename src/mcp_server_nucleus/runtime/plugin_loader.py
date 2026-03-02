"""
PluginLoader v2: The Airlock.
Strictly controls how tools enter the Nucleus Runtime.

Strategic Role:
- Enforces "Air Gap": Only loads tools explicitly allowed by Manifest.
- Enforces "Governance": Wraps all tools in BudgetGuard.
- Isolates Agents: Scopes loading to specific Agent Directory.
"""

import sys
import importlib.util
import logging
from pathlib import Path
from typing import List
from .capabilities.base import Capability
from .budget import BudgetAuditor, BudgetGuard

logger = logging.getLogger("nucleus.plugins")

class PluginLoader:
    def __init__(self, brain_path: Path, auditor: BudgetAuditor):
        self.brain_path = brain_path
        self.auditor = auditor
        self.installed_tools_dir = brain_path / "tools" / "installed"

    def load_agent_tools(self, agent_id: str, authorized_modules: List[str]) -> List[Capability]:
        """
        Loads allowed tools for a specific agent.
        Wraps them in BudgetGuard(default=$0.00).
        """
        agent_dir = self.installed_tools_dir / agent_id
        
        if not agent_dir.exists():
            logger.warning(f"⚠️ Agent directory not found: {agent_dir}")
            return []
            
        logger.info(f"🔌 Accessing Agent Airlock: {agent_id}")
        
        # Ensure the directory is in python path
        sys.path.append(str(agent_dir))
        
        loaded_plugins = []
        
        for module_name in authorized_modules:
            # Construct expected file path
            tool_path = agent_dir / f"{module_name}.py"
            
            if not tool_path.exists():
                logger.error(f"❌ Missing authorized tool: {module_name} in {agent_dir}")
                continue
                
            try:
                # Import Module
                spec = importlib.util.spec_from_file_location(module_name, tool_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "get_capability"):
                        cap = module.get_capability()
                        if isinstance(cap, Capability):
                            
                            # --- GOVERNANCE WRAPPER ---
                            # By default, tools have $0.00 budget until Policy grants more.
                            # We wrap immediately to ensure safety.
                            guarded_cap = BudgetGuard(
                                inner=cap,
                                auditor=self.auditor,
                                agent_id=agent_id,
                                max_budget_usd=0.0 # Default Deny
                            )
                            
                            loaded_plugins.append(guarded_cap)
                            logger.info(f"    ✅ Loaded & Secured: {cap.name}")
                        else:
                            logger.warning(f"    ⚠️ Invalid Capability in {module_name}")
                    else:
                        logger.warning(f"    ℹ️ Missing entry point in {module_name}")
                        
            except Exception as e:
                logger.error(f"    ❌ Failed to load {module_name}: {e}")
                
        return loaded_plugins
