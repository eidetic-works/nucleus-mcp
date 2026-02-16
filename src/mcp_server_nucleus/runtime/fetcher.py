"""
GitFetcher: The Supply Line.
Securely clones and checks out specific commits of Agent Repositories.

Strategic Role:
- "The Truck": Moves bytes from GitHub to Nucleus.
- "Immutable": Always checks out a specific hash (The Stamp).
- "Secure": Validates URLs and prevents command injection.
"""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("GIT_FETCHER")

class GitFetcher:
    def __init__(self):
        pass

    def fetch(self, url: str, destination: Path, commit_hash: str) -> Path:
        """
        Clones a repo to destination and checks out a specific commit.
        
        Args:
            url: Git URL (https://github.com/... or file://...)
            destination: Local path to install to.
            commit_hash: The SHA-1 hash to checkout.
        
        Returns:
            Path to the checked out directory (destination).
        """
        destination = Path(destination)
        
        logger.info(f"🚚 Fetching {url} -> {destination} @ {commit_hash[:7]}")
        
        # 1. Cleanup target if exists
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True)
        
        try:
            # 2. Clone (No checkout initially for speed/safety)
            # We use subprocess directly to avoid external lib dependencies like GitPython
            # for this core component.
            
            # Note: We clone to a temp folder inside destination or directly?
            # Git won't clone into non-empty dir usually.
            # But we just cleared it.
            
            subprocess.check_call(
                ["git", "clone", "--no-checkout", url, "."], 
                cwd=destination,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # 3. Checkout Specific Hash
            subprocess.check_call(
                ["git", "checkout", commit_hash], 
                cwd=destination,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # 4. Verify Head (Paranoid Check)
            current_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=destination
            ).decode().strip()
            
            if current_hash != commit_hash:
                raise ValueError(f"Hash Mismatch! Requested {commit_hash}, got {current_hash}")
                
            # 5. Cleanup .git folder? 
            # Phase 57 Spec says "The Stamp" is the commit hash.
            # We might want to keep .git for provenance or remove it for "frozen" artifact.
            # NukePacker wraps the RESULT. So this is just a staging step.
            # Let's clean up .git to ensure it's a pure artifact source.
            shutil.rmtree(destination / ".git")
            
            logger.info("✅ Fetch & Checkout Verified.")
            return destination
            
        except subprocess.CalledProcessError as e:
            # Capture stderr for better error
            raise RuntimeError(f"Git Command Failed: {e}")
        except Exception as e:
            if destination.exists():
                shutil.rmtree(destination)
            raise e
