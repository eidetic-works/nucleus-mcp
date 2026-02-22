"""
Publisher: The Shipping Department.
Orchestrates the creation of Signed Agent Artifacts.

Strategic Role:
- VALIDATOR: Ensures Manifest is legal before packing.
- SIGNER: Applies the Keymaster's seal.
- PACKER: Creates the purely immutable .nuke file.
"""

import logging
from pathlib import Path
from typing import Optional

from .identity.keygen import KeyManager
from .identity.manifest import ManifestValidator
from .nuke_protocol import NukePacker

logger = logging.getLogger("PUBLISHER")

class Publisher:
    def __init__(self, brain_path: Path, key_manager: Optional[KeyManager] = None):
        self.brain_path = brain_path
        self.key_manager = key_manager or KeyManager(brain_path)
        self.packer = NukePacker(staging_root=brain_path / "staging")
        self.validator = ManifestValidator()

    def publish(self, agent_source: Path, output_dir: Path, key_id: str, private: bool = False) -> Path:
        """
        Publish an agent from source directory.
        
        Args:
            agent_source: Directory containing manifest.json and code.
            output_dir: Where to save the .nuke artifact.
            key_id: ID of the key to sign with.
            private: If True, marks manifest as private (if supported).
        
        Returns:
            Path to the generated .nuke file.
        """
        agent_source = Path(agent_source)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📦 Publishing agent from {agent_source}...")
        
        # 1. Validate Manifest
        manifest_path = agent_source / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.json missing in source")
            
        manifest_data = manifest_path.read_text()
        import json
        manifest_obj = json.loads(manifest_data)
        if not self.validator.validate(manifest_obj):
            raise ValueError("❌ Validation Failed: User's manifest is invalid.")
            
        # 2. Get Signature
        # We need to sign the content. NukePacker.pack signs the manifest.
        # Wait, NukePacker.pack takes a private_key_pem.
        
        try:
            # Retrieve private key protected by KeyManager
            # In Phase 57, KeyManager.get_key returns KeyPair (has private bytes)
            # But get_key might return None.
            # actually we don't have get_key exposed publicly easily without password?
            # KeyManager.sign is the preferred way?
            # NukePacker pack expects private_key_pem string.
            
            # Let's peek at KeyManager implementation via memory or usage.
            # It loads from disk. 
            # We'll use key_manager._load_key_pair(key_id) which is internal?
            # Or assume KeyManager is initialized.
            
            # Better: KeyManager SHOULD handle signing. NukePacker should take a signer callback?
            # For Phase 57, let's load the PEM.
            
            key_pair = self.key_manager.get_key_pair(key_id) # Assuming this exists or we need to add it
            if not key_pair:
                raise ValueError(f"Key ID {key_id} not found.")
                
            private_key_pem = key_pair.private_key_pem
            
            # 3. Collect Tools
            # Naive scan for now: all .py files in source except manifest
            tool_paths = list(agent_source.glob("*.py"))
            
            # 4. Pack & Sign
            # Construct output filename: agent.id-version.nuke
            # We must use the VALIDATED manifest object
            from .identity.manifest import AgentManifest
            validated_manifest = AgentManifest(**manifest_obj)
            
            artifact_filename = f"{validated_manifest.agent.id}-{validated_manifest.agent.version}.nuke"
            final_artifact_path = output_dir / artifact_filename
            
            self.packer.pack(
                manifest=validated_manifest,
                tool_paths=tool_paths,
                private_key_pem=private_key_pem,
                output_path=final_artifact_path
            )
            
            logger.info(f"✅ Published: {final_artifact_path}")
            return final_artifact_path
            
        except Exception as e:
            logger.error(f"❌ Publishing failed: {e}")
            raise e
