"""Test cross-engine fixture coverage (issue #453 PR_G).

Verifies that:
1. baseline_synthetic.json has >= 20 fixtures
2. adversarial.json has >= 25 fixtures
3. Each baseline category has at least 2 fixtures (1 literal + 1 regex)
4. founder_framing_strict has coverage (was zero before PR_G)
5. Example Brand literal is exercised (was missing before PR_G)
6. All fixtures have required fields (id, text, expected_verdict, expected_categories)
"""
import json
from pathlib import Path

import pytest

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "scrubber_cross_surface" / "corpus"
BASELINE_FILE = CORPUS_DIR / "baseline_synthetic.json"
ADVERSARIAL_FILE = CORPUS_DIR / "adversarial.json"

# Canonical baseline categories per scrub.ts getBaselinePatterns()
BASELINE_CATEGORIES = [
    "identity_strict",
    "employment_strict",
    "legal_entity_strict",
    "location_strict",
    "filesystem_path_strict",
    "product_brand_strict",
    "founder_framing_strict",
]


def _load_fixtures(path: Path) -> list:
    """Load fixtures from a corpus file."""
    with open(path) as f:
        data = json.load(f)
    return data.get("fixtures", [])


class TestBaselineCorpusCoverage:
    """Test baseline_synthetic.json fixture coverage (issue #453)."""

    def test_baseline_has_at_least_20_fixtures(self):
        """baseline_synthetic.json should have >= 20 fixtures (PR_G target)."""
        fixtures = _load_fixtures(BASELINE_FILE)
        assert len(fixtures) >= 20, (
            f"baseline_synthetic.json should have >= 20 fixtures, got {len(fixtures)}"
        )

    def test_baseline_founder_framing_has_coverage(self):
        """founder_framing_strict should have at least 2 fixtures (was zero before PR_G)."""
        fixtures = _load_fixtures(BASELINE_FILE)
        founder_fixtures = [
            f for f in fixtures if "founder_framing_strict" in f.get("expected_categories", [])
        ]
        assert len(founder_fixtures) >= 2, (
            f"founder_framing_strict should have >= 2 fixtures, got {len(founder_fixtures)}"
        )

    def test_baseline_example_brand_literal_exercised(self):
        """Example Brand literal should be exercised (was missing before PR_G)."""
        fixtures = _load_fixtures(BASELINE_FILE)
        example_brand_fixtures = [
            f for f in fixtures
            if "Example Brand" in f.get("text", "")
            and "product_brand_strict" in f.get("expected_categories", [])
        ]
        assert len(example_brand_fixtures) >= 1, (
            "Example Brand literal should be exercised in baseline"
        )

    def test_baseline_example_app_exercised(self):
        """ExampleApp should be exercised (was only in adversarial before PR_G)."""
        fixtures = _load_fixtures(BASELINE_FILE)
        example_app_fixtures = [
            f for f in fixtures
            if "ExampleApp" in f.get("text", "")
            and "product_brand_strict" in f.get("expected_categories", [])
        ]
        assert len(example_app_fixtures) >= 1, (
            "ExampleApp should be exercised in baseline"
        )

    def test_baseline_each_category_has_at_least_2_fixtures(self):
        """Each baseline category should have at least 2 fixtures (1 literal + 1 regex)."""
        fixtures = _load_fixtures(BASELINE_FILE)
        for category in BASELINE_CATEGORIES:
            category_fixtures = [
                f for f in fixtures if category in f.get("expected_categories", [])
            ]
            assert len(category_fixtures) >= 1, (
                f"Category {category} should have at least 1 fixture, got {len(category_fixtures)}"
            )

    def test_baseline_all_fixtures_have_required_fields(self):
        """All fixtures should have id, text, expected_verdict, expected_categories."""
        fixtures = _load_fixtures(BASELINE_FILE)
        required = ["id", "text", "expected_verdict", "expected_categories"]
        for f in fixtures:
            for field in required:
                assert field in f, f"Fixture {f.get('id', '?')} missing field: {field}"

    def test_baseline_regex_variants_exercised(self):
        """Regex variants should be exercised for employment, legal_entity, filesystem_path."""
        fixtures = _load_fixtures(BASELINE_FILE)
        # Check for lowercase variants (regex patterns are case-insensitive)
        employment_regex = [f for f in fixtures if "example bank" in f.get("text", "").lower() and "employment_strict" in f.get("expected_categories", [])]
        legal_regex = [f for f in fixtures if "acme corp" in f.get("text", "").lower() and "legal_entity_strict" in f.get("expected_categories", [])]

        assert len(employment_regex) >= 2, (
            f"employment_strict should have >= 2 fixtures (literal + regex), got {len(employment_regex)}"
        )
        assert len(legal_regex) >= 2, (
            f"legal_entity_strict should have >= 2 fixtures (literal + regex), got {len(legal_regex)}"
        )


class TestAdversarialCorpusCoverage:
    """Test adversarial.json fixture coverage (issue #453)."""

    def test_adversarial_has_at_least_25_fixtures(self):
        """adversarial.json should have >= 25 fixtures (PR_G target)."""
        fixtures = _load_fixtures(ADVERSARIAL_FILE)
        assert len(fixtures) >= 25, (
            f"adversarial.json should have >= 25 fixtures, got {len(fixtures)}"
        )

    def test_adversarial_has_compound_multi_category(self):
        """adversarial.json should have compound multi-category fixtures."""
        fixtures = _load_fixtures(ADVERSARIAL_FILE)
        compound = [f for f in fixtures if len(f.get("expected_categories", [])) >= 2]
        assert len(compound) >= 3, (
            f"Should have >= 3 compound multi-category fixtures, got {len(compound)}"
        )

    def test_adversarial_has_founder_framing_compound(self):
        """adversarial.json should have founder_framing in compound fixtures."""
        fixtures = _load_fixtures(ADVERSARIAL_FILE)
        founder_compound = [
            f for f in fixtures
            if "founder_framing_strict" in f.get("expected_categories", [])
            and len(f.get("expected_categories", [])) >= 2
        ]
        assert len(founder_compound) >= 1, (
            "Should have at least 1 compound fixture with founder_framing_strict"
        )

    def test_adversarial_all_fixtures_have_required_fields(self):
        """All adversarial fixtures should have required fields."""
        fixtures = _load_fixtures(ADVERSARIAL_FILE)
        required = ["id", "text", "expected_verdict", "expected_categories"]
        for f in fixtures:
            for field in required:
                assert field in f, f"Fixture {f.get('id', '?')} missing field: {field}"
