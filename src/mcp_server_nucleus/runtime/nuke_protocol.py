"""
The .nuke Protocol (Nucleus Universal Knowledge Exchange).
Phase 57 Implementation.

Format: ZIP Archive
Structure:
  /manifest.json (AgentManifest Schema)
  /signature.sig (Ed25519 Signature of manifest.json)
  /tools/ (Python Code)
"""

import json
import logging
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict

from .identity.keygen import KeyManager
from .identity.manifest import AgentManifest, ManifestValidator

logger = logging.getLogger("NUKE_PROTOCOL")

class NukePacker:
    """
    Creates signed .nuke artifacts.
    """
    def __init__(self, staging_root: Path):
        self.staging_root = staging_root
        self.staging_root.mkdir(parents=True, exist_ok=True)
        self.key_manager = KeyManager()

    def pack(self, manifest: AgentManifest, tool_paths: List[Path], private_key_pem: str, output_path: Path) -> Path:
        """
        Bundles an agent into a .nuke file.
        """
        logger.info(f"📦 Packing Agent: {manifest.agent.id} -> {output_path}")
        
        # 1. Create Staging Area
        with tempfile.TemporaryDirectory(dir=self.staging_root) as tmp_dir:
            staging_dir = Path(tmp_dir)
            tools_dir = staging_dir / "tools"
            tools_dir.mkdir()
            
            # 2. Add Tools
            for tool_path in tool_paths:
                if not tool_path.exists():
                    raise FileNotFoundError(f"Tool not found: {tool_path}")
                shutil.copy2(tool_path, tools_dir / tool_path.name)
                
            # 3. Write Manifest
            manifest_json = manifest.model_dump_json(indent=2)
            manifest_path = staging_dir / "manifest.json"
            manifest_path.write_text(manifest_json)
            
            # 4. Sign Manifest
            # We sign the BYTES of the manifest.json file to ensure exact integrity
            manifest_bytes = manifest_path.read_bytes()
            signature = self.key_manager.sign(private_key_pem, manifest_bytes)
            
            # Save signature as hex string
            (staging_dir / "signature.sig").write_text(signature.hex())
            
            # 5. Zip it
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in staging_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(staging_dir))
                        
        logger.info(f"✅ Created {output_path} ({output_path.stat().st_size} bytes)")
        return output_path

class NukeLoader:
    """
    Loads and Verifies .nuke artifacts.
    """
    def __init__(self, install_root: Path):
        self.install_root = install_root
        self.key_manager = KeyManager()
        self.installed_tools_dir = install_root / "tools" / "installed"
        self.installed_tools_dir.mkdir(parents=True, exist_ok=True)

    def load(self, nuke_path: Path, trusted_keys: Dict[str, str]) -> AgentManifest:
        """
        Verifies and Unpacks a .nuke file.
        trusted_keys: Dict[KeyID, PublicKeyPEM]
        """
        logger.info(f"🔓 Loading .nuke: {nuke_path}")
        
        with zipfile.ZipFile(nuke_path, 'r') as zf:
            # 1. Extract Manifest & Sig to memory
            try:
                manifest_bytes = zf.read("manifest.json")
                signature_hex = zf.read("signature.sig").decode().strip()
                signature_bytes = bytes.fromhex(signature_hex)
            except KeyError:
                raise ValueError("❌ Invalid .nuke: Missing manifest or signature")
                
            # 2. Parse Manifest
            try:
                manifest_dict = json.loads(manifest_bytes)
                manifest = ManifestValidator.validate(manifest_dict)
            except Exception as e:
                raise ValueError(f"❌ Invalid Manifest: {e}")
                
            # 3. Lookup Public Key
            # In Phase 57, we assume the publisher ID is embedded in the manifest or we trust the signer
            # For this MVP, we verify using the TRUSTED_KEYS passed in.
            # We treat the Key ID as the signer.
            
            # Note: The Manifest doesn't strictly have a "signer_id" field in our schema yet.
            # We rely on the KeyManager logic: We need the Public Key corresponding to the Private Key that signed it.
            # In a real PKI, the Manifest would contain the KeyID, or the Repository would provide it.
            # Let's try every trusted key. If ANY valid key verifies it, we are good.
            
            verified = False
            signer_key_id = None
            
            for key_id, pub_pem in trusted_keys.items():
                if self.key_manager.verify(pub_pem, signature_bytes, manifest_bytes):
                    verified = True
                    signer_key_id = key_id
                    break
                    
            if not verified:
                raise PermissionError("❌ SIGNATURE VERIFICATION FAILED: No trusted key matches signature")
                
            logger.info(f"✅ Verified by KeyID: {signer_key_id}")
            
            # 4. Install Tools
            # We namespace them by Agent ID to avoid collisions
            agent_dir = self.installed_tools_dir / manifest.agent.id
            if agent_dir.exists():
                shutil.rmtree(agent_dir)
            agent_dir.mkdir()
            
            for file in zf.namelist():
                if file.startswith("tools/") and file.endswith(".py"):
                    # Extract tool code
                    tool_content = zf.read(file)
                    tool_name = Path(file).name
                    (agent_dir / tool_name).write_bytes(tool_content)
                    
            logger.info(f"    -> Installed {len(list(agent_dir.glob('*.py')))} tools to {agent_dir}")
            
            return manifest
