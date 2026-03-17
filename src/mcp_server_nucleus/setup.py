import os
import sys
import shutil
from pathlib import Path

def get_shell_profile():
    """Detect shell and return corresponding profile path."""
    shell = os.environ.get('SHELL', '')
    home = Path.home()
    
    if 'zsh' in shell:
        return home / '.zshrc'
    elif 'bash' in shell:
        bash_profile = home / '.bash_profile'
        if bash_profile.exists():
            return bash_profile
        return home / '.bashrc'
    return None

from .runtime.common import get_brain_path, get_nucleus_bin_path

def install_nucleus_path(dry_run=False):
    """Safely inject Nucleus environment into shell profile."""
    profile = get_shell_profile()
    if not profile:
        print("❌ Could not detect shell or profile. Please add paths manually.")
        return False

    # Standard locations to add to PATH
    bin_path = get_nucleus_bin_path()
    brain_path = str(get_brain_path())
    
    # Check current PATH to avoid redundant additions
    current_path = os.environ.get('PATH', '').split(os.pathsep)
    path_to_add = bin_path if bin_path not in current_path and Path(bin_path).exists() else None
    
    path_exports = "\n# Node/Nucleus MCP Path Integration\n"
    if path_to_add:
        path_exports += f'export PATH="{path_to_add}:$PATH"\n'
    
    # Use $HOME for portability if possible
    home_str = str(Path.home())
    if brain_path.startswith(home_str):
        portable_brain = brain_path.replace(home_str, "$HOME")
        path_exports += f'export NUCLEUS_BRAIN_PATH="{portable_brain}"\n'
    else:
        path_exports += f'export NUCLEUS_BRAIN_PATH="{brain_path}"\n'
    
    # Alias for legacy support
    path_exports += 'export NUCLEAR_BRAIN_PATH="$NUCLEUS_BRAIN_PATH"\n'
    
    # Autocompletion Integration
    runtime_dir = Path(__file__).parent / "runtime"
    completion_script = runtime_dir / "completions.sh"
    if completion_script.exists():
        path_exports += f'\n# Nucleus Autocompletion\n'
        path_exports += f'[ -f "{completion_script}" ] && source "{completion_script}"\n'

    if dry_run:
        print(f"--- DRY RUN: Would append to {profile} ---")
        print(path_exports)
        return True

    try:
        # Check if already contains Nucleus block to avoid double injection
        content = profile.read_text() if profile.exists() else ""
        if "Nucleus MCP Path Integration" in content:
            print(f"ℹ️ Shell profile {profile} already has Nucleus integration. Updating...")
            # Ideally we would replace the block, but for MVP we just inform.
            # print("To reconfigure, remove the existing block and run again.")
            return True

        with open(profile, "a") as f:
            f.write(path_exports)
        
        print(f"✅ Successfully updated {profile}")
        print(f"📍 Brain Root: {brain_path}")
        print("🔥 Restart your terminal or run: source " + str(profile))
        return True
    except Exception as e:
        print(f"❌ Failed to update {profile}: {e}")
        return False

if __name__ == "__main__":
    install_nucleus_path()
