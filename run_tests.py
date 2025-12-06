#!/usr/bin/env python3
"""
Test runner script for the automated testing suite.

This script executes the complete test suite for the gamification and referral modules,
providing clear output of the results.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Execute the pytest test suite and display results."""
    print("="*60)
    print("🤖 BOT TESTING SUITE EXECUTION")
    print("="*60)
    print()
    
    # Change to the project directory
    project_dir = Path(__file__).parent.absolute()
    os.chdir(project_dir)
    
    print("📋 Executing Gamification & Referral Tests...")
    print()
    
    # Command to run the specific test file
    cmd = [sys.executable, "-m", "pytest", "tests/test_gamification.py", "-v"]
    
    try:
        # Execute the test command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        # Print stdout and stderr from pytest
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
            
        print()
        print("="*60)
        
        # Determine success based on return code
        if result.returncode == 0:
            print("✅ ALL TESTS PASSED! Gamification & Referral modules are working correctly.")
            print("="*60)
            return True
        else:
            print("❌ SOME TESTS FAILED! Please check the output above for details.")
            print("="*60)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Test execution timed out!")
        return False
    except FileNotFoundError:
        print("❌ pytest not found! Please ensure pytest is installed:")
        print("   pip install pytest pytest-asyncio aiosqlite")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_full_test_suite():
    """Execute the full test suite including all tests."""
    print("\n" + "="*60)
    print("🧪 EXECUTING FULL TEST SUITE")
    print("="*60)
    print()

    print("📋 Running all tests in the project...")
    print()
    
    # Command to run all tests
    cmd = [sys.executable, "-m", "pytest", "-v"]
    
    try:
        # Execute the test command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout for full suite
        )
        
        # Print stdout and stderr from pytest
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
            
        print()
        print("="*60)
        
        # Determine success based on return code
        if result.returncode == 0:
            print("✅ ALL TESTS IN SUITE PASSED!")
        else:
            print("⚠️  SOME TESTS IN SUITE FAILED (This may include pre-existing failing tests)")
        print("="*60)
        return result.returncode == 0
            
    except subprocess.TimeoutExpired:
        print("⏰ Full test suite execution timed out!")
        return False
    except FileNotFoundError:
        print("❌ pytest not found! Please ensure pytest is installed:")
        print("   pip install pytest pytest-asyncio aiosqlite")
        return False
    except Exception as e:
        print(f"❌ Error running full test suite: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting Bot Test Execution Script...")
    print()
    
    # Run the gamification tests specifically
    gamification_success = run_tests()
    
    # Also run the full test suite to see overall status
    full_suite_success = run_full_test_suite()
    
    print("\n📊 SUMMARY:")
    print(f"   Gamification Tests: {'✅ PASSED' if gamification_success else '❌ FAILED'}")
    print(f"   Full Test Suite:    {'✅ PASSED' if full_suite_success else '⚠️  SOME FAILED'}")
    
    print("\n💡 To run only gamification tests: python -m pytest tests/test_gamification.py -v")
    print("💡 To run all tests: python -m pytest -v")
    print()
    
    # Exit with appropriate code based on gamification tests (the main focus)
    sys.exit(0 if gamification_success else 1)