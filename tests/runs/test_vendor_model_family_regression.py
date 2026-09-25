def test_model_family_is_derived_from_selected_model_id():
    from mcp_server_nucleus.runtime.vendor_dispatch import resolve_model_family

    assert resolve_model_family("swe-2-max") == "swe"
    assert resolve_model_family("swe-1-7") == "swe"
    assert resolve_model_family("glm-5-2") == "glm"
    assert resolve_model_family("gemini-3.7-flash") == "gemini"
    assert resolve_model_family("gpt-5.6-terra") == "gpt"
    assert resolve_model_family("claude-sonnet-5-high") == "claude"


def test_devin_registry_default_family_matches_default_model():
    from mcp_server_nucleus.runtime.vendor_dispatch import VENDOR_SPECS

    spec = VENDOR_SPECS["devin"]
    assert spec.default_model == "swe-2-max"
    assert spec.model == "swe"
    assert "swe-1-7" in spec.models
    assert "glm-5-2" in spec.models


def test_executor_exposes_selected_model_family():
    from mcp_server_nucleus.runtime.vendor_dispatch import VendorCLIExecutor

    swe = VendorCLIExecutor("devin", "task", model="swe-1-7")
    glm = VendorCLIExecutor("devin", "task", model="glm-5-2")

    assert swe.model_family == "swe"
    assert glm.model_family == "glm"


def test_vendor_result_normalizes_mismatched_family():
    from mcp_server_nucleus.runtime.vendor_dispatch import VendorResult

    result = VendorResult("devin", "glm", 0, "ok", "done", 1.0, model_id="swe-1-7")

    assert result.model == "swe"
    assert result.to_dict()["model_family"] == "swe"
