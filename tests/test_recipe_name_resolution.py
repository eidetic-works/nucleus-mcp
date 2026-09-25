"""
Recipe name-resolution tests for load_recipe.

Covers the three resolution stages in runtime/recipes.py:
  1. Exact file-stem lookup
  2. Case-insensitive display-name match
  3. Slug match via _slugify()
"""
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.recipes import (
    RecipeNotFoundError,
    _slugify,
    list_recipes,
    load_recipe,
)


@pytest.mark.parametrize(
    "left, right, expected_name",
    [
        ("founder", "Founder OS", "Founder OS"),
        ("founder", "founder os", "Founder OS"),
        ("founder", "founder-os", "Founder OS"),
        ("sre", "SRE Brain", "SRE Brain"),
        ("sre", "sre brain", "SRE Brain"),
        ("sre", "sre-brain", "SRE Brain"),
        ("adhd", "ADHD Brain", "ADHD Brain"),
        ("adhd", "adhd brain", "ADHD Brain"),
        ("adhd", "adhd-brain", "ADHD Brain"),
    ],
)
def test_parametrized_opposed_pair_resolution(left, right, expected_name):
    """Each "opposed" pair of name forms resolves to the same recipe."""
    left_data = load_recipe(left)
    right_data = load_recipe(right)

    assert left_data["name"] == expected_name
    assert right_data["name"] == expected_name
    assert left_data["_source_path"] == right_data["_source_path"]


def test_absent_name_failure_with_accepted_token_check():
    """A missing recipe raises RecipeNotFoundError and names all accepted tokens."""
    missing = "definitely_not_a_recipe_12345"

    with pytest.raises(RecipeNotFoundError) as exc:
        load_recipe(missing)

    message = str(exc.value)
    assert f"Recipe '{missing}' not found" in message

    for recipe in list_recipes():
        display_name = recipe["name"]
        stem = Path(recipe["path"]).stem
        assert display_name in message, f"display name {display_name!r} missing from error"
        assert stem in message, f"stem {stem!r} missing from error"


def test_exact_key_unchanged():
    """Loading by the exact file stem returns the canonical display name unchanged."""
    data = load_recipe("founder")
    assert data["name"] == "Founder OS"
    assert data["_source_path"].endswith("founder.yaml")

    data = load_recipe("sre")
    assert data["name"] == "SRE Brain"
    assert data["_source_path"].endswith("sre.yaml")

    data = load_recipe("adhd")
    assert data["name"] == "ADHD Brain"
    assert data["_source_path"].endswith("adhd.yaml")


def test_full_accepted_tokens_listing():
    """Every accepted token (stem, display name, slug) for every recipe resolves."""
    for recipe in list_recipes():
        display_name = recipe["name"]
        stem = Path(recipe["path"]).stem
        slug = _slugify(display_name)

        tokens = {stem, display_name, slug}
        for token in tokens:
            data = load_recipe(token)
            assert data["name"] == display_name, (
                f"token {token!r} resolved to {data['name']!r}, expected {display_name!r}"
            )
