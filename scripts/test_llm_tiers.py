#!/usr/bin/env python3
"""
Nucleus LLM Tier Benchmark Script
=================================
Tests all LLM tier configurations and reports availability, latency, and cost estimates.

Usage:
    python test_llm_tiers.py [--save]
    
Options:
    --save    Save results to .brain/tier_status.json
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime

# Add the src path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load tier configuration
TIERS_CONFIG_PATH = Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "llm_tiers.json"

def load_tiers_config():
    """Load tier definitions from JSON config."""
    if TIERS_CONFIG_PATH.exists():
        with open(TIERS_CONFIG_PATH) as f:
            return json.load(f)
    else:
        # Fallback hardcoded config
        return {
            "tiers": {
                "premium": {"model": "gemini-3-pro", "platform": "vertex"},
                "standard": {"model": "gemini-2.5-flash", "platform": "vertex"},
                "economy": {"model": "gemini-2.5-flash-lite", "platform": "vertex"},
                "local_paid": {"model": "gemini-2.5-flash", "platform": "api_key"},
                "local_free": {"model": "gemini-2.0-flash", "platform": "api_key"},
            }
        }


def test_tier(tier_name: str, config: dict) -> dict:
    """Test a single LLM tier and return status."""
    model = config.get("model", "gemini-2.5-flash")
    platform = config.get("platform", "vertex")
    
    result = {
        "tier": tier_name,
        "model": model,
        "platform": platform,
        "status": "UNKNOWN",
        "latency_ms": None,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Import here to avoid issues if dependencies aren't installed
        from google import genai
        
        start_time = time.time()
        
        if platform == "vertex":
            # Vertex AI Mode - Uses ADC
            project_id = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0894185576")
            location = os.environ.get("GCP_LOCATION", "us-central1")
            client = genai.Client(vertexai=True, project=project_id, location=location)
        else:
            # API Key Mode
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                result["status"] = "NO_API_KEY"
                result["error"] = "GEMINI_API_KEY environment variable not set"
                return result
            client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        
        # Simple test prompt
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly one word: OK"
        )
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Check response
        if hasattr(response, 'text') and response.text:
            result["status"] = "SUCCESS"
            result["latency_ms"] = round(latency_ms, 2)
            result["response_preview"] = response.text[:50]
        else:
            result["status"] = "EMPTY_RESPONSE"
            result["latency_ms"] = round(latency_ms, 2)
            
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            result["status"] = "QUOTA_EXCEEDED"
        elif "401" in error_str or "403" in error_str or "UNAUTHENTICATED" in error_str:
            result["status"] = "AUTH_FAILED"
        elif "404" in error_str or "not found" in error_str.lower():
            result["status"] = "MODEL_NOT_FOUND"
        elif "credentials" in error_str.lower():
            result["status"] = "ADC_MISSING"
        else:
            result["status"] = "ERROR"
        result["error"] = error_str[:200]
    
    return result


def run_all_tests() -> dict:
    """Run tests on all configured tiers."""
    config = load_tiers_config()
    tiers = config.get("tiers", {})
    
    results = {
        "run_timestamp": datetime.now().isoformat(),
        "environment": {
            "GEMINI_API_KEY_SET": bool(os.environ.get("GEMINI_API_KEY")),
            "GCP_PROJECT_ID": os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0894185576"),
            "FORCE_VERTEX": os.environ.get("FORCE_VERTEX", "1"),
        },
        "tier_results": {},
        "available_tiers": [],
        "unavailable_tiers": [],
    }
    
    print("\n" + "="*60)
    print("🧪 NUCLEUS LLM TIER BENCHMARK")
    print("="*60)
    
    for tier_name, tier_config in tiers.items():
        print(f"\n🔬 Testing tier: {tier_name} ({tier_config.get('model', 'unknown')})")
        result = test_tier(tier_name, tier_config)
        results["tier_results"][tier_name] = result
        
        if result["status"] == "SUCCESS":
            results["available_tiers"].append(tier_name)
            print(f"   ✅ SUCCESS - Latency: {result['latency_ms']}ms")
        else:
            results["unavailable_tiers"].append(tier_name)
            print(f"   ❌ {result['status']} - {result.get('error', 'No details')[:80]}")
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Available: {', '.join(results['available_tiers']) or 'None'}")
    print(f"Unavailable: {', '.join(results['unavailable_tiers']) or 'None'}")
    
    # Recommend best tier
    if results["available_tiers"]:
        for preferred in ["standard", "economy", "premium", "local_paid", "local_free"]:
            if preferred in results["available_tiers"]:
                print(f"\n🏆 Recommended tier: {preferred}")
                results["recommended_tier"] = preferred
                break
    else:
        print("\n⚠️  No tiers available! Check your credentials.")
        results["recommended_tier"] = None
    
    return results


def main():
    results = run_all_tests()
    
    # Save if requested
    if "--save" in sys.argv:
        brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", "/Users/lokeshgarg/ai-mvp-backend/.brain"))
        output_path = brain_path / "tier_status.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")
    
    # Return exit code based on availability
    if results["available_tiers"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
