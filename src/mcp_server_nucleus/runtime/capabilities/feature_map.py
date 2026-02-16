from typing import List, Dict, Any, Optional
import json
import os
import time
from pathlib import Path
from .base import Capability

class FeatureMap(Capability):
    def __init__(self):
        # Determine brain path
        brain_path_str = os.environ.get("NUCLEAR_BRAIN_PATH")
        if not brain_path_str:
            # Fallback for dev/verification if not set (though highly recommended)
            brain_path_str = "/Users/lokeshgarg/.gemini/antigravity/brain/7c654df4-b83e-43f9-8620-f15868ec39d1"
            
        self.brain_path = Path(brain_path_str)
        self.features_dir = self.brain_path / "features"
    
    @property
    def name(self) -> str:
        return "feature_map"

    @property
    def description(self) -> str:
        return "Manage the feature inventory to prevent 'feature amnesia'. Track what exists, status, and how to test."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_add_feature",
                "description": "Add a new feature to the product's feature map.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string", "description": "'gentlequest' or 'nucleus'"},
                        "name": {"type": "string", "description": "Human-readable feature name"},
                        "description": {"type": "string", "description": "What the feature does"},
                        "source": {"type": "string", "description": "Where it lives (e.g., 'gentlequest_app', 'pypi_mcp')"},
                        "version": {"type": "string", "description": "Which version it shipped in"},
                        "status": {"type": "string", "description": "development/staged/production/released"},
                        "how_to_test": {"type": "array", "items": {"type": "string"}, "description": "List of test steps"},
                        "expected_result": {"type": "string", "description": "What should happen when testing"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Searchable tags"}
                    },
                    "required": ["product", "name", "description", "source", "version", "how_to_test", "expected_result"]
                }
            },
            {
                "name": "brain_list_features",
                "description": "List all features, optionally filtered.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string", "description": "Filter by product"},
                        "status": {"type": "string", "description": "Filter by status"},
                        "tag": {"type": "string", "description": "Filter by tag"}
                    }
                }
            },
            {
                "name": "brain_get_feature",
                "description": "Get a specific feature by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {"type": "string", "description": "The feature ID (snake_case)"}
                    },
                    "required": ["feature_id"]
                }
            },
            {
                "name": "brain_update_feature",
                "description": "Update a feature's fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {"type": "string", "description": "Feature to update"},
                        "status": {"type": "string", "description": "New status"},
                        "description": {"type": "string", "description": "New description"},
                        "version": {"type": "string", "description": "New version"}
                    },
                    "required": ["feature_id"]
                }
            },
            {
                "name": "brain_mark_validated",
                "description": "Mark a feature as validated after testing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {"type": "string", "description": "Feature that was tested"},
                        "result": {"type": "string", "description": "'passed' or 'failed'"}
                    },
                    "required": ["feature_id", "result"]
                }
            },
            {
                "name": "brain_search_features",
                "description": "Search features by name, description, or tags.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> Any:
        try:
            if tool_name == "brain_add_feature":
                return self._add_feature(args)
            elif tool_name == "brain_list_features":
                return self._list_features(args)
            elif tool_name == "brain_get_feature":
                return self._get_feature(args.get("feature_id"))
            elif tool_name == "brain_update_feature":
                return self._update_feature(args)
            elif tool_name == "brain_mark_validated":
                return self._mark_validated(args.get("feature_id"), args.get("result"))
            elif tool_name == "brain_search_features":
                return self._search_features(args.get("query"))
            return f"Tool {tool_name} not found"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    # --- Internal Helpers ---

    def _get_store_path(self, product: str) -> Path:
        return self.features_dir / f"{product}.json"

    def _load_store(self, product: str) -> Dict:
        path = self._get_store_path(product)
        if not path.exists():
            return {"product": product, "features": []}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {"product": product, "features": []}

    def _save_store(self, product: str, data: Dict):
        path = self._get_store_path(product)
        # atomic write
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def _generate_id(self, name: str) -> str:
        # Simple snake_case conversion
        return name.lower().replace(" ", "_").replace("-", "_")

    # --- Core Logic ---

    def _add_feature(self, args: Dict) -> Dict:
        product = args.get("product").lower()
        if product not in ["gentlequest", "nucleus"]:
            # Default to gentlequest if unknown product? 
            # Or enforce schema. Let's strictly enforce supported products for MVP
            if product not in ["gentlequest", "nucleus"]:
                 # Just treat it as a new product file
                 pass
        
        store = self._load_store(product)
        
        feature_id = self._generate_id(args.get("name"))
        
        # Check if exists
        for f in store["features"]:
            if f["id"] == feature_id:
                return {"error": f"Feature '{feature_id}' already exists. Use update."}

        new_feature = {
            "id": feature_id,
            "name": args.get("name"),
            "description": args.get("description"),
            "product": product,
            "source": args.get("source"),
            "version": args.get("version"),
            "status": args.get("status", "development"),
            "how_to_test": args.get("how_to_test", []),
            "expected_result": args.get("expected_result", ""),
            "tags": args.get("tags", []),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "last_validated": None,
            "validation_result": None
        }

        store["features"].append(new_feature)
        store["total_features"] = len(store["features"])
        store["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        self._save_store(product, store)
        return {"success": True, "feature": new_feature}

    def _list_features(self, args: Dict) -> List[Dict]:
        products = ["gentlequest", "nucleus"]
        target_product = args.get("product")
        if target_product:
            products = [target_product]
        
        all_features = []
        for p in products:
            store = self._load_store(p)
            all_features.extend(store.get("features", []))
            
        # Filters
        status = args.get("status")
        tag = args.get("tag")
        
        if status:
            all_features = [f for f in all_features if f.get("status") == status]
        if tag:
            all_features = [f for f in all_features if tag in f.get("tags", [])]
            
        return all_features[:50] # Limit output

    def _get_find_feature(self, feature_id: str) -> Optional[Dict]:
        # Helper to search across all products
        for p in ["gentlequest", "nucleus"]:
            store = self._load_store(p)
            for f in store.get("features", []):
                if f["id"] == feature_id:
                    return f, p, store
        return None, None, None

    def _get_feature(self, feature_id: str) -> Any:
        f, _, _ = self._get_find_feature(feature_id)
        if f:
            return f
        return {"error": f"Feature '{feature_id}' not found"}

    def _update_feature(self, args: Dict) -> Any:
        feature_id = args.get("feature_id")
        f, product, store = self._get_find_feature(feature_id)
        
        if not f:
            return {"error": f"Feature '{feature_id}' not found"}
            
        # Update fields
        valid_updates = ["status", "description", "version"]
        updated = False
        for key in valid_updates:
            if key in args:
                f[key] = args[key]
                updated = True
                
        if updated:
            self._save_store(product, store)
            return {"success": True, "feature": f}
        return {"success": False, "message": "No changes made"}

    def _mark_validated(self, feature_id: str, result: str) -> Any:
        f, product, store = self._get_find_feature(feature_id)
        if not f:
            return {"error": f"Feature '{feature_id}' not found"}
            
        f["last_validated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        f["validation_result"] = result
        
        self._save_store(product, store)
        return {"success": True, "feature_id": feature_id, "result": result, "timestamp": f["last_validated"]}

    def _search_features(self, query: str) -> List[Dict]:
        query = query.lower()
        all_features = self._list_features({})
        
        matches = []
        for f in all_features:
            text = f"{f['name']} {f['description']} {' '.join(f.get('tags', []))}".lower()
            if query in text:
                matches.append(f)
        
        # Sort by relevance? For now just return matches
        return matches[:20]
