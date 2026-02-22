"""
Feature Map Operations - Product feature inventory management.

Extracted from __init__.py monolith (v1.0.7 decomposition).
"""

import json
import time
import logging
from typing import Dict, List
from pathlib import Path

from .common import get_brain_path

logger = logging.getLogger("nucleus.features")


def _get_features_path(product: str) -> Path:
    """Get path to product's features.json file."""
    brain = get_brain_path()
    return brain / "features" / f"{product}.json"


def _load_features(product: str) -> Dict:
    """Load features for a product."""
    path = _get_features_path(product)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"product": product, "last_updated": None, "total_features": 0, "features": []}


def _save_features(product: str, data: Dict) -> None:
    """Save features for a product."""
    path = _get_features_path(product)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    data["total_features"] = len(data.get("features", []))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _add_feature(product: str, name: str, description: str, source: str, 
                 version: str, how_to_test: List[str], expected_result: str,
                 status: str = "development", **kwargs) -> Dict:
    """Add a new feature to the product's feature map."""
    try:
        data = _load_features(product)
        
        # Generate ID from name
        feature_id = name.lower().replace(" ", "_").replace("-", "_")
        feature_id = "".join(c for c in feature_id if c.isalnum() or c == "_")
        
        # Check for duplicates
        if any(f.get("id") == feature_id for f in data.get("features", [])):
            return {"error": f"Feature '{feature_id}' already exists"}
        
        # Build feature dict
        feature = {
            "id": feature_id,
            "name": name,
            "description": description,
            "product": product,
            "source": source,
            "version": version,
            "status": status,
            "how_to_test": how_to_test,
            "expected_result": expected_result,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "last_validated": None,
            "validation_result": None
        }
        
        # Add optional fields
        for key in ["tier", "deployed_at", "deployed_url", "released_at", 
                    "pypi_url", "files_changed", "commit_sha", "tags"]:
            if key in kwargs:
                feature[key] = kwargs[key]
        
        data.setdefault("features", []).append(feature)
        _save_features(product, data)
        
        return {"success": True, "feature": feature}
    except Exception as e:
        return {"error": str(e)}


def _list_features(product: str = None, status: str = None, tag: str = None) -> Dict:
    """List features with optional filters."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        if not features_dir.exists():
            return {"features": [], "total": 0}
        
        all_features = []
        
        # Get all product files or just the specified one
        if product:
            products = [product]
        else:
            products = [f.stem for f in features_dir.glob("*.json")]
        
        for p in products:
            data = _load_features(p)
            for feature in data.get("features", []):
                # Apply filters
                if status and feature.get("status") != status:
                    continue
                if tag and tag not in feature.get("tags", []):
                    continue
                all_features.append(feature)
        
        return {"features": all_features, "total": len(all_features)}
    except Exception as e:
        return {"error": str(e)}


def _get_feature(feature_id: str) -> Dict:
    """Get a specific feature by ID."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        if not features_dir.exists():
            return {"error": f"Feature '{feature_id}' not found"}
        
        for json_file in features_dir.glob("*.json"):
            data = _load_features(json_file.stem)
            for feature in data.get("features", []):
                if feature.get("id") == feature_id:
                    return {"feature": feature}
        
        return {"error": f"Feature '{feature_id}' not found"}
    except Exception as e:
        return {"error": str(e)}


def _update_feature(feature_id: str, **updates) -> Dict:
    """Update a feature."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        for json_file in features_dir.glob("*.json"):
            product = json_file.stem
            data = _load_features(product)
            
            for i, feature in enumerate(data.get("features", [])):
                if feature.get("id") == feature_id:
                    # Apply updates
                    for key, value in updates.items():
                        data["features"][i][key] = value
                    
                    _save_features(product, data)
                    return {"success": True, "feature": data["features"][i]}
        
        return {"error": f"Feature '{feature_id}' not found"}
    except Exception as e:
        return {"error": str(e)}


def _mark_validated(feature_id: str, result: str) -> Dict:
    """Mark a feature as validated."""
    if result not in ["passed", "failed"]:
        return {"error": "Result must be 'passed' or 'failed'"}
    
    return _update_feature(
        feature_id,
        last_validated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        validation_result=result
    )


def _search_features(query: str) -> Dict:
    """Search features by name, description, or tags."""
    try:
        result = _list_features()
        if "error" in result:
            return result
        
        query_lower = query.lower()
        matches = []
        
        for feature in result.get("features", []):
            # Search in name, description, tags
            searchable = " ".join([
                feature.get("name", ""),
                feature.get("description", ""),
                " ".join(feature.get("tags", []))
            ]).lower()
            
            if query_lower in searchable:
                matches.append(feature)
        
        return {"features": matches, "total": len(matches), "query": query}
    except Exception as e:
        return {"error": str(e)}
