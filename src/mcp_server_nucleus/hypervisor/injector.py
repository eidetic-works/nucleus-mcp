
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Injector:
    """
    The Nucleus Hypervisor Injection Primitive (Layer 2).
    Dynamically injects context and identity into running IDEs by manipulating
    configuration files that support hot-reloading (e.g., .vscode/settings.json).
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.vscode_settings_path = self.workspace_root / ".vscode" / "settings.json"

    def _ensure_vscode_dir(self):
        if not self.vscode_settings_path.parent.exists():
            self.vscode_settings_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_settings(self) -> Dict[str, Any]:
        if not self.vscode_settings_path.exists():
            return {}
        try:
            # Handle comments in JSON if necessary (standard json lib doesn't, but VSCode allows them)
            # For now, assuming standard JSON or we overwrite.
            # Ideally use a comment-preserving parser, but simple JSON is safer for machine-control.
            return json.loads(self.vscode_settings_path.read_text())
        except Exception as e:
            logger.warning(f"Failed to read settings.json: {e}")
            return {}

    def _write_settings(self, settings: Dict[str, Any]) -> bool:
        try:
            self._ensure_vscode_dir()
            self.vscode_settings_path.write_text(json.dumps(settings, indent=4))
            return True
        except Exception as e:
            logger.error(f"Failed to write settings.json: {e}")
            return False

    def inject_identity(self, identity: str, color_hex: str) -> bool:
        """
        Injects visual identity markers into VSCode settings.
        """
        settings = self._read_settings()
        
        # Inject standard visual cues
        settings["workbench.colorCustomizations"] = settings.get("workbench.colorCustomizations", {})
        settings["workbench.colorCustomizations"]["titleBar.activeBackground"] = color_hex
        settings["workbench.colorCustomizations"]["titleBar.activeForeground"] = "#ffffff"
        settings["workbench.colorCustomizations"]["activityBar.background"] = color_hex
        
        # Inject status bar message (if possible via extension, or just window title)
        settings["window.title"] = f"[{identity.upper()}] ${{rootName}}"
        
        # Inject context-specific file exclusions if needed
        # e.g., if Red Team, hide 'build' folder?
        
        return self._write_settings(settings)

    def reset_identity(self) -> bool:
        """
        Removes injected identity markers.
        """
        settings = self._read_settings()
        
        if "workbench.colorCustomizations" in settings:
            # Remove our specific keys
            for key in ["titleBar.activeBackground", "titleBar.activeForeground", "activityBar.background"]:
                settings["workbench.colorCustomizations"].pop(key, None)
            
            # If empty, remove the whole object
            if not settings["workbench.colorCustomizations"]:
                del settings["workbench.colorCustomizations"]
                
        if "window.title" in settings:
            del settings["window.title"]
            
        return self._write_settings(settings)
