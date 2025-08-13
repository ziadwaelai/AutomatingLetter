"""
AutomatingLetter Test Runner
===========================

Comprehensive test runner for the AutomatingLetter project.
Runs all available tests and provides detailed reporting.
"""

import sys
import os
import unittest
import time
from io import StringIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def run_all_tests():
    """Run all available tests in the test directory."""
    print("\n🚀 AutomatingLetter Complete Test Suite Runner")
    print("=" * 60)
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Import available test modules
    test_modules = []
    
    try:
        from test_complete_system import run_complete_test_suite
        test_modules.append(("Complete System Tests", run_complete_test_suite))
        print("✅ Loaded: Complete System Tests")
    except ImportError as e:
        print(f"⚠️  Could not load Complete System Tests: {e}")
    
    try:
        from test_unit_components import run_unit_tests
        test_modules.append(("Unit Component Tests", run_unit_tests))
        print("✅ Loaded: Unit Component Tests")
    except ImportError as e:
        print(f"⚠️  Could not load Unit Component Tests: {e}")
    
    try:
        from test_chat import TestChatService
        suite = unittest.TestLoader().loadTestsFromTestCase(TestChatService)
        test_modules.append(("Chat Service Tests", lambda: unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()))
        print("✅ Loaded: Chat Service Tests")
    except ImportError as e:
        print(f"⚠️  Could not load Chat Service Tests: {e}")
    
    try:
        from test_complete_workflow import TestCompleteWorkflow
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCompleteWorkflow)
        test_modules.append(("Complete Workflow Tests", lambda: unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()))
        print("✅ Loaded: Complete Workflow Tests")
    except ImportError as e:
        print(f"⚠️  Could not load Complete Workflow Tests: {e}")
    
    if not test_modules:
        print("❌ No test modules could be loaded!")
        return False
    
    print(f"\n📊 Running {len(test_modules)} test suites...")
    print("=" * 60)
    
    # Run all test modules
    results = []
    total_start_time = time.time()
    
    for test_name, test_function in test_modules:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        
        start_time = time.time()
        try:
            success = test_function()
            elapsed_time = time.time() - start_time
            results.append((test_name, success, elapsed_time, None))
            
            if success:
                print(f"✅ {test_name} PASSED ({elapsed_time:.2f}s)")
            else:
                print(f"❌ {test_name} FAILED ({elapsed_time:.2f}s)")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            results.append((test_name, False, elapsed_time, str(e)))
            print(f"💥 {test_name} ERROR ({elapsed_time:.2f}s): {e}")
    
    total_elapsed_time = time.time() - total_start_time
    
    # Print final summary
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, success, _, _ in results if success)
    failed_count = len(results) - passed_count
    
    print(f"Total Test Suites: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Success Rate: {(passed_count / len(results) * 100):.1f}%")
    print(f"Total Time: {total_elapsed_time:.2f}s")
    
    print(f"\n📋 Detailed Results:")
    for test_name, success, elapsed_time, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {test_name} ({elapsed_time:.2f}s)")
        if error:
            print(f"      Error: {error}")
    
    if passed_count == len(results):
        print(f"\n🎉 ALL TEST SUITES PASSED! AutomatingLetter is working perfectly!")
        return True
    else:
        print(f"\n⚠️  {failed_count} test suite(s) failed. Please check the issues above.")
        return False


def run_quick_tests():
    """Run only quick unit tests without requiring server."""
    print("\n⚡ Quick Unit Tests (No Server Required)")
    print("=" * 50)
    
    try:
        from test_unit_components import run_unit_tests
        return run_unit_tests()
    except ImportError as e:
        print(f"Could not load unit tests: {e}")
        return False


def run_integration_tests():
    """Run integration tests that require running server."""
    print("\n🔗 Integration Tests (Server Required)")
    print("=" * 50)
    
    try:
        from test_complete_system import run_complete_test_suite
        return run_complete_test_suite()
    except ImportError as e:
        print(f"Could not load integration tests: {e}")
        return False


def main():
    """Main test runner with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AutomatingLetter Test Runner')
    parser.add_argument('--quick', action='store_true', 
                       help='Run only quick unit tests (no server required)')
    parser.add_argument('--integration', action='store_true',
                       help='Run only integration tests (server required)')
    parser.add_argument('--all', action='store_true', default=True,
                       help='Run all available tests (default)')
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_tests()
    elif args.integration:
        success = run_integration_tests()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
