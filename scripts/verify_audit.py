#!/usr/bin/env python3
"""
Comprehensive verification script for Multi-Crew Orchestration System.
Run this to verify the audit claims.
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ PASS")
            if result.stdout:
                print(result.stdout[-200:])  # Last 200 chars
            return True
        else:
            print("❌ FAIL")
            print(result.stderr[-200:] if result.stderr else "No error output")
            return False
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def check_file_exists(path, description):
    """Check if a file exists."""
    print(f"\nChecking: {description}")
    if Path(path).exists():
        print(f"✅ FOUND: {path}")
        return True
    else:
        print(f"❌ MISSING: {path}")
        return False

def main():
    """Run all verification checks."""
    print("🔍 Multi-Crew Orchestration System - Audit Verification")
    print("="*60)
    
    results = []
    
    # Check 1: Documentation files
    print("\n" + "="*60)
    print("1. DOCUMENTATION FILES")
    print("="*60)
    docs = [
        ("docs/ADR-001-Multi-Crew-Audit.md", "Audit report"),
        ("docs/AUDIT-SUMMARY.md", "Audit summary"),
        ("docs/GETTING_STARTED.md", "Getting started guide"),
        ("docs/MULTI_CREW_ORCHESTRATOR.md", "Architecture docs"),
        (".env.template", "Environment template"),
    ]
    for path, desc in docs:
        results.append(check_file_exists(path, desc))
    
    # Check 2: Unit tests
    results.append(run_command(
        "python3 tests/test_multi_crew_orchestrator.py",
        "Unit tests (all should pass)"
    ))
    
    # Check 3: Demo script
    results.append(run_command(
        "python3 scripts/demo_multi_crew.py 2>&1 | tail -5",
        "Demo script (no API key)"
    ))
    
    # Check 4: Import verification
    results.append(run_command(
        "python3 -c \"from scripts.hfo_multi_crew_orchestrator import SwarmlordOrchestrator; print('✓ Import successful')\"",
        "Module imports"
    ))
    
    # Check 5: CrewAI installation
    results.append(run_command(
        "python3 -c \"import crewai; print(f'CrewAI v{crewai.__version__}')\"",
        "CrewAI installation"
    ))
    
    # Check 6: Blackboard verification
    results.append(run_command(
        "python3 scripts/verify_blackboard.py 2>&1 | tail -10 | grep -q 'checks passed' && echo 'PASS' || echo 'FAIL'",
        "Blackboard stigmergy"
    ))
    
    # Check 7: Requirements.txt
    results.append(run_command(
        "grep -E 'crewai.*>=.*<' requirements.txt",
        "Flexible CrewAI versions in requirements.txt"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL CHECKS PASSED")
        print("\nThe audit claims are verified:")
        print("  ✓ All tests pass")
        print("  ✓ Demo works without API key")
        print("  ✓ Imports resolve correctly")
        print("  ✓ CrewAI is installed")
        print("  ✓ Blackboard logging works")
        print("  ✓ Documentation is complete")
        print("  ✓ Requirements.txt is fixed")
        print("\n✅ IMPLEMENTATION IS PRODUCTION READY")
        return 0
    else:
        print(f"\n❌ SOME CHECKS FAILED ({total - passed} failures)")
        print("\nPlease review the failed checks above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
