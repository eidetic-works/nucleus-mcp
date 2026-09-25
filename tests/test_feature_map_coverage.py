"""
Coverage tests for runtime/capabilities/feature_map.py
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.capabilities.feature_map import FeatureMap


@pytest.fixture
def feature_map(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return FeatureMap()


@pytest.fixture
def fm_with_data(feature_map):
    """FeatureMap with a pre-populated product store."""
    feature_map._save_store("nucleus", {
        "product": "nucleus",
        "features": [
            {
                "id": "test_feature",
                "name": "Test Feature",
                "description": "A test feature",
                "product": "nucleus",
                "source": "cli",
                "version": "1.0",
                "status": "production",
                "how_to_test": ["run test"],
                "expected_result": "passes",
                "tags": ["test", "core"],
                "created_at": "2024-01-01T00:00:00",
                "last_validated": None,
                "validation_result": None
            },
            {
                "id": "beta_feature",
                "name": "Beta Feature",
                "description": "A beta feature",
                "product": "nucleus",
                "source": "mcp",
                "version": "0.9",
                "status": "development",
                "how_to_test": [],
                "expected_result": "works",
                "tags": ["beta"],
                "created_at": "2024-01-01T00:00:00",
                "last_validated": None,
                "validation_result": None
            }
        ],
        "total_features": 2,
        "last_updated": "2024-01-01T00:00:00"
    })
    return feature_map


# ---------------------------------------------------------------------------
# Properties & Init
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, feature_map):
        assert feature_map.name == "feature_map"

    def test_description(self, feature_map):
        assert "feature" in feature_map.description.lower()

    def test_init_default_brain_path(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        fm = FeatureMap()
        assert fm.brain_path == Path(".brain")

    def test_init_with_env(self, feature_map, tmp_path):
        assert feature_map.brain_path == tmp_path / ".brain"
        assert feature_map.features_dir == feature_map.brain_path / "features"


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_six_tools(self, feature_map):
        tools = feature_map.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_add_feature" in names
        assert "brain_list_features" in names
        assert "brain_get_feature" in names
        assert "brain_update_feature" in names
        assert "brain_mark_validated" in names
        assert "brain_search_features" in names

    def test_add_feature_required(self, feature_map):
        tools = feature_map.get_tools()
        tool = [t for t in tools if t["name"] == "brain_add_feature"][0]
        required = tool["parameters"]["required"]
        assert "product" in required
        assert "name" in required
        assert "description" in required

    def test_mark_validated_required(self, feature_map):
        tools = feature_map.get_tools()
        tool = [t for t in tools if t["name"] == "brain_mark_validated"][0]
        assert "feature_id" in tool["parameters"]["required"]
        assert "result" in tool["parameters"]["required"]


# ---------------------------------------------------------------------------
# _get_store_path / _load_store / _save_store
# ---------------------------------------------------------------------------
class TestStoreOperations:
    def test_get_store_path(self, feature_map):
        path = feature_map._get_store_path("myproduct")
        assert path.name == "myproduct.json"
        assert path.parent == feature_map.features_dir

    def test_load_store_nonexistent(self, feature_map):
        result = feature_map._load_store("nonexistent")
        assert result == {"product": "nonexistent", "features": []}

    def test_load_store_existing(self, fm_with_data):
        result = fm_with_data._load_store("nucleus")
        assert result["product"] == "nucleus"
        assert len(result["features"]) == 2

    def test_load_store_corrupt_json(self, feature_map):
        feature_map.features_dir.mkdir(parents=True, exist_ok=True)
        (feature_map.features_dir / "corrupt.json").write_text("not valid json{{{")
        result = feature_map._load_store("corrupt")
        assert result == {"product": "corrupt", "features": []}

    def test_save_store_creates_dir(self, feature_map):
        data = {"product": "test", "features": []}
        feature_map._save_store("test", data)
        path = feature_map._get_store_path("test")
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["product"] == "test"


# ---------------------------------------------------------------------------
# _generate_id
# ---------------------------------------------------------------------------
class TestGenerateId:
    def test_simple_name(self, feature_map):
        assert feature_map._generate_id("Simple Name") == "simple_name"

    def test_with_hyphens(self, feature_map):
        assert feature_map._generate_id("Feature-Name") == "feature_name"

    def test_already_snake_case(self, feature_map):
        assert feature_map._generate_id("already_snake") == "already_snake"

    def test_mixed_case(self, feature_map):
        assert feature_map._generate_id("My Feature Name") == "my_feature_name"


# ---------------------------------------------------------------------------
# _add_feature
# ---------------------------------------------------------------------------
class TestAddFeature:
    def test_add_feature_success(self, feature_map):
        result = feature_map._add_feature({
            "product": "nucleus",
            "name": "New Feature",
            "description": "Does something",
            "source": "cli",
            "version": "1.0",
            "how_to_test": ["step 1"],
            "expected_result": "works"
        })
        assert result["success"] is True
        assert result["feature"]["id"] == "new_feature"
        assert result["feature"]["status"] == "development"  # default

    def test_add_feature_default_product(self, feature_map):
        result = feature_map._add_feature({
            "name": "Auto Product",
            "description": "test",
            "source": "cli",
            "version": "1.0",
            "how_to_test": [],
            "expected_result": "ok"
        })
        assert result["feature"]["product"] == "nucleus"

    def test_add_feature_duplicate(self, fm_with_data):
        result = fm_with_data._add_feature({
            "product": "nucleus",
            "name": "Test Feature",
            "description": "dup",
            "source": "x",
            "version": "1",
            "how_to_test": [],
            "expected_result": "x"
        })
        assert "error" in result
        assert "already exists" in result["error"]

    def test_add_feature_with_tags(self, feature_map):
        result = feature_map._add_feature({
            "product": "nucleus",
            "name": "Tagged Feature",
            "description": "test",
            "source": "cli",
            "version": "1.0",
            "how_to_test": [],
            "expected_result": "ok",
            "tags": ["new", "cool"],
            "status": "staged"
        })
        assert result["feature"]["tags"] == ["new", "cool"]
        assert result["feature"]["status"] == "staged"

    def test_add_feature_updates_total(self, feature_map):
        feature_map._add_feature({
            "product": "nucleus", "name": "F1", "description": "d",
            "source": "s", "version": "v", "how_to_test": [], "expected_result": "e"
        })
        feature_map._add_feature({
            "product": "nucleus", "name": "F2", "description": "d",
            "source": "s", "version": "v", "how_to_test": [], "expected_result": "e"
        })
        store = feature_map._load_store("nucleus")
        assert store["total_features"] == 2


# ---------------------------------------------------------------------------
# _list_features
# ---------------------------------------------------------------------------
class TestListFeatures:
    def test_list_all(self, fm_with_data):
        result = fm_with_data._list_features({})
        assert len(result) == 2

    def test_list_by_product(self, fm_with_data):
        result = fm_with_data._list_features({"product": "nucleus"})
        assert len(result) == 2

    def test_list_by_status(self, fm_with_data):
        result = fm_with_data._list_features({"status": "production"})
        assert len(result) == 1
        assert result[0]["id"] == "test_feature"

    def test_list_by_tag(self, fm_with_data):
        result = fm_with_data._list_features({"tag": "beta"})
        assert len(result) == 1
        assert result[0]["id"] == "beta_feature"

    def test_list_by_product_and_status(self, fm_with_data):
        result = fm_with_data._list_features({"product": "nucleus", "status": "development"})
        assert len(result) == 1
        assert result[0]["id"] == "beta_feature"

    def test_list_empty_store(self, feature_map):
        result = feature_map._list_features({"product": "nucleus"})
        assert result == []

    def test_list_limit_50(self, fm_with_data):
        """Verify output is capped at 50."""
        # Add many features
        for i in range(60):
            fm_with_data._add_feature({
                "product": "nucleus", "name": f"Feature {i}",
                "description": "d", "source": "s", "version": "v",
                "how_to_test": [], "expected_result": "e"
            })
        result = fm_with_data._list_features({"product": "nucleus"})
        assert len(result) == 50


# ---------------------------------------------------------------------------
# _discover_products
# ---------------------------------------------------------------------------
class TestDiscoverProducts:
    def test_discover_returns_nucleus_fallback(self, feature_map):
        """_discover_products uses self._brain which doesn't exist, returns ['nucleus']."""
        result = feature_map._discover_products()
        assert result == ["nucleus"]

    def test_discover_with_brain_attribute(self, feature_map, monkeypatch):
        """When self._brain is set, discover works."""
        feature_map._brain = feature_map.brain_path
        features_dir = feature_map.brain_path / "features"
        features_dir.mkdir(parents=True)
        (features_dir / "product_a.json").write_text("{}")
        (features_dir / "product_b.json").write_text("{}")
        result = feature_map._discover_products()
        assert "product_a" in result
        assert "product_b" in result

    def test_discover_exception_returns_nucleus(self, feature_map):
        """When _brain dir doesn't exist, returns nucleus fallback."""
        feature_map._brain = Path("/nonexistent/path/xyz")
        result = feature_map._discover_products()
        assert result == ["nucleus"]


# ---------------------------------------------------------------------------
# _get_feature / _get_find_feature
# ---------------------------------------------------------------------------
class TestGetFeature:
    def test_get_existing(self, fm_with_data):
        result = fm_with_data._get_feature("test_feature")
        assert result["id"] == "test_feature"

    def test_get_nonexistent(self, fm_with_data):
        result = fm_with_data._get_feature("no_such_feature")
        assert "error" in result
        assert "not found" in result["error"]

    def test_get_find_feature_returns_tuple(self, fm_with_data):
        f, product, store = fm_with_data._get_find_feature("test_feature")
        assert f is not None
        assert product == "nucleus"
        assert store is not None

    def test_get_find_feature_not_found(self, fm_with_data):
        f, product, store = fm_with_data._get_find_feature("nonexistent")
        assert f is None
        assert product is None
        assert store is None


# ---------------------------------------------------------------------------
# _update_feature
# ---------------------------------------------------------------------------
class TestUpdateFeature:
    def test_update_status(self, fm_with_data):
        result = fm_with_data._update_feature({
            "feature_id": "test_feature",
            "status": "released"
        })
        assert result["success"] is True
        assert result["feature"]["status"] == "released"

    def test_update_description(self, fm_with_data):
        result = fm_with_data._update_feature({
            "feature_id": "test_feature",
            "description": "Updated description"
        })
        assert result["success"] is True
        assert result["feature"]["description"] == "Updated description"

    def test_update_version(self, fm_with_data):
        result = fm_with_data._update_feature({
            "feature_id": "test_feature",
            "version": "2.0"
        })
        assert result["success"] is True
        assert result["feature"]["version"] == "2.0"

    def test_update_nonexistent(self, fm_with_data):
        result = fm_with_data._update_feature({
            "feature_id": "nonexistent",
            "status": "production"
        })
        assert "error" in result
        assert "not found" in result["error"]

    def test_update_no_changes(self, fm_with_data):
        result = fm_with_data._update_feature({"feature_id": "test_feature"})
        assert result["success"] is False
        assert "No changes" in result["message"]

    def test_update_multiple_fields(self, fm_with_data):
        result = fm_with_data._update_feature({
            "feature_id": "test_feature",
            "status": "released",
            "version": "3.0",
            "description": "new desc"
        })
        assert result["success"] is True
        assert result["feature"]["status"] == "released"
        assert result["feature"]["version"] == "3.0"


# ---------------------------------------------------------------------------
# _mark_validated
# ---------------------------------------------------------------------------
class TestMarkValidated:
    def test_mark_validated_passed(self, fm_with_data):
        result = fm_with_data._mark_validated("test_feature", "passed")
        assert result["success"] is True
        assert result["result"] == "passed"
        assert result["timestamp"] is not None

    def test_mark_validated_failed(self, fm_with_data):
        result = fm_with_data._mark_validated("beta_feature", "failed")
        assert result["success"] is True
        assert result["result"] == "failed"

    def test_mark_validated_nonexistent(self, fm_with_data):
        result = fm_with_data._mark_validated("nonexistent", "passed")
        assert "error" in result
        assert "not found" in result["error"]

    def test_mark_validated_persists(self, fm_with_data):
        fm_with_data._mark_validated("test_feature", "passed")
        store = fm_with_data._load_store("nucleus")
        feature = [f for f in store["features"] if f["id"] == "test_feature"][0]
        assert feature["last_validated"] is not None
        assert feature["validation_result"] == "passed"


# ---------------------------------------------------------------------------
# _search_features
# ---------------------------------------------------------------------------
class TestSearchFeatures:
    def test_search_by_name(self, fm_with_data):
        result = fm_with_data._search_features("Test")
        assert len(result) == 1
        assert result[0]["id"] == "test_feature"

    def test_search_by_description(self, fm_with_data):
        result = fm_with_data._search_features("beta")
        assert len(result) == 1
        assert result[0]["id"] == "beta_feature"

    def test_search_by_tag(self, fm_with_data):
        result = fm_with_data._search_features("core")
        assert len(result) == 1
        assert result[0]["id"] == "test_feature"

    def test_search_no_matches(self, fm_with_data):
        result = fm_with_data._search_features("nonexistent_query_xyz")
        assert result == []

    def test_search_case_insensitive(self, fm_with_data):
        result = fm_with_data._search_features("TEST")
        assert len(result) == 1

    def test_search_limit_20(self, fm_with_data):
        """Verify search results are capped at 20."""
        for i in range(25):
            fm_with_data._add_feature({
                "product": "nucleus", "name": f"Searchable {i}",
                "description": "searchable", "source": "s", "version": "v",
                "how_to_test": [], "expected_result": "e"
            })
        result = fm_with_data._search_features("searchable")
        assert len(result) <= 20


# ---------------------------------------------------------------------------
# execute_tool dispatch
# ---------------------------------------------------------------------------
class TestExecuteTool:
    def test_dispatch_add(self, feature_map):
        result = feature_map.execute_tool("brain_add_feature", {
            "product": "nucleus", "name": "Dispatch Test",
            "description": "d", "source": "s", "version": "v",
            "how_to_test": [], "expected_result": "e"
        })
        assert isinstance(result, dict)
        assert result.get("success") is True

    def test_dispatch_list(self, fm_with_data):
        result = fm_with_data.execute_tool("brain_list_features", {})
        assert isinstance(result, list)

    def test_dispatch_get(self, fm_with_data):
        result = fm_with_data.execute_tool("brain_get_feature", {"feature_id": "test_feature"})
        assert result["id"] == "test_feature"

    def test_dispatch_update(self, fm_with_data):
        result = fm_with_data.execute_tool("brain_update_feature", {
            "feature_id": "test_feature", "status": "released"
        })
        assert result["success"] is True

    def test_dispatch_mark_validated(self, fm_with_data):
        result = fm_with_data.execute_tool("brain_mark_validated", {
            "feature_id": "test_feature", "result": "passed"
        })
        assert result["success"] is True

    def test_dispatch_search(self, fm_with_data):
        result = fm_with_data.execute_tool("brain_search_features", {"query": "test"})
        assert isinstance(result, list)

    def test_dispatch_unknown(self, feature_map):
        result = feature_map.execute_tool("nonexistent", {})
        assert "not found" in result

    def test_dispatch_exception_handled(self, feature_map):
        """When an internal method raises, execute_tool catches it."""
        with patch.object(feature_map, "_add_feature", side_effect=Exception("Boom")):
            result = feature_map.execute_tool("brain_add_feature", {})
            assert "Error" in result
