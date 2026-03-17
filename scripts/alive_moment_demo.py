#!/usr/bin/env python3
"""
Alive Moment Demo Script — The ONE workflow that makes Nucleus alive.

This script demonstrates the complete Alive Workflow in under 60 seconds:
1. Morning Brief — What should I work on today?
2. Context Switch Tracking — Am I staying focused?
3. End-of-Day Capture — Persist learnings for tomorrow
4. Compounding Loop — See the 7-day workflow status

Design Thinking Reference:
  "Nucleus will not come alive through more tools, more memory, or more architecture.
   It will come alive through ONE provable workflow that the founder uses every day."
  — EXHAUSTIVE_DESIGN_THINKING_OUTPUT.md, Stage 4

Usage:
    NUCLEAR_BRAIN_PATH=/path/to/.brain python3 scripts/alive_moment_demo.py
    
    Or with the CLI:
    nucleus morning-brief
    nucleus loop
    nucleus end-of-day "What I accomplished today"
"""

import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def print_banner(title: str):
    """Print a section banner."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step: int, title: str):
    """Print a step header."""
    print()
    print(f"┌{'─' * 68}┐")
    print(f"│ STEP {step}: {title:<58} │")
    print(f"└{'─' * 68}┘")


def demo_morning_brief():
    """Demonstrate the Morning Brief workflow."""
    print_step(1, "MORNING BRIEF — What should I work on?")
    print()
    
    from mcp_server_nucleus.runtime.morning_brief_ops import _morning_brief_impl
    
    start = time.time()
    result = _morning_brief_impl()
    elapsed = (time.time() - start) * 1000
    
    # Print the formatted brief
    print(result.get("formatted", "No brief generated"))
    print()
    print(f"⚡ Brief generated in {elapsed:.1f}ms")
    
    return result


def demo_context_switch():
    """Demonstrate the Context Switch Detector."""
    print_step(2, "ADHD GUARDRAIL — Am I staying focused?")
    print()
    
    from mcp_server_nucleus.runtime.depth_ops import _context_switch, _context_switch_status
    
    # Simulate some context switches
    contexts = [
        "Morning Brief Implementation",
        "Checking emails",
        "Back to coding",
        "Reading documentation",
    ]
    
    print("Simulating context switches...")
    for ctx in contexts[:2]:  # Only do 2 to avoid triggering alerts in demo
        result = _context_switch(ctx)
        status = result.get("warning_level", "safe")
        emoji = "🟢" if status == "safe" else "🟡" if status == "caution" else "🔴"
        print(f"  {emoji} Switched to: {ctx}")
        time.sleep(0.1)
    
    # Show status
    print()
    status = _context_switch_status()
    print(f"Focus Status: {status.get('status', 'Unknown')}")
    print(f"Context Switches: {status.get('switch_count', 0)}/{status.get('max_switches', 5)}")
    print(f"Recommendation: {status.get('recommendation', 'N/A')}")


def demo_compounding_loop():
    """Demonstrate the Compounding v0 Loop status."""
    print_step(3, "COMPOUNDING LOOP — Where am I in the 7-day cycle?")
    print()
    
    from mcp_server_nucleus.runtime.compounding_loop import _compounding_loop_status_impl
    
    result = _compounding_loop_status_impl()
    print(result.get("formatted", "No loop status"))


def demo_end_of_day():
    """Demonstrate the End-of-Day Capture (dry run)."""
    print_step(4, "END-OF-DAY CAPTURE — Persist learnings")
    print()
    
    print("Example usage:")
    print()
    print('  brain_end_of_day(')
    print('      summary="Implemented the Alive Workflow. Morning Brief works.",')
    print('      key_decisions=["ADHD guardrails integrated", "CLI commands added"],')
    print('      blockers=[]')
    print('  )')
    print()
    print("This creates engrams that will surface in tomorrow's Morning Brief,")
    print("creating the COMPOUNDING EFFECT that makes each day faster.")


def demo_session_inject():
    """Demonstrate Session-Start Context Injection."""
    print_step(5, "SESSION INJECT — Load yesterday's context")
    print()
    
    from mcp_server_nucleus.runtime.compounding_loop import _session_start_inject_impl
    
    result = _session_start_inject_impl()
    print(result.get("context", "No context available"))
    print()
    print(f"Engrams loaded: {result.get('engram_count', 0)}")
    print(f"Active tasks: {result.get('task_count', 0)}")


def main():
    """Run the complete Alive Moment demo."""
    print_banner("🧬 NUCLEUS ALIVE MOMENT DEMO")
    print()
    print("This demo shows the ONE workflow that brings Nucleus to life.")
    print("From 'I just opened my IDE' to 'I know what to do' in <60 seconds.")
    print()
    
    # Check environment
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not brain_path:
        print("❌ ERROR: NUCLEAR_BRAIN_PATH not set")
        print()
        print("Usage:")
        print("  export NUCLEAR_BRAIN_PATH=/path/to/.brain")
        print("  python3 scripts/alive_moment_demo.py")
        sys.exit(1)
    
    print(f"Brain Path: {brain_path}")
    print()
    
    total_start = time.time()
    
    try:
        # Run demo steps
        demo_morning_brief()
        demo_context_switch()
        demo_compounding_loop()
        demo_end_of_day()
        demo_session_inject()
        
        total_elapsed = time.time() - total_start
        
        print_banner("🎯 DEMO COMPLETE")
        print()
        print(f"Total time: {total_elapsed:.1f} seconds")
        print()
        print("Key Insight:")
        print("  Nucleus remembers yesterday's decisions and applies them today")
        print("  WITHOUT being told. This is the 'Alive Moment'.")
        print()
        print("CLI Commands:")
        print("  • nucleus morning-brief    — Your daily brief")
        print("  • nucleus loop             — 7-day compounding status")
        print("  • nucleus end-of-day \"...\" — Capture learnings")
        print()
        print("MCP Tools:")
        print("  • brain_morning_brief      — THE daily workflow")
        print("  • brain_compounding_status — Day-of-week guidance")
        print("  • brain_context_switch     — ADHD guardrail")
        print("  • brain_end_of_day         — Persist learnings")
        print("  • brain_session_inject     — Load yesterday's context")
        print()
        print("=" * 70)
        print("  'Nucleus should compound on itself.'")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
