#!/usr/bin/env python3
"""
Comprehensive test runner for the Dashboard E2E tests.
Runs all test suites and generates a detailed report.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class Color:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print formatted header."""
    print(f"\n{Color.HEADER}{Color.BOLD}{'='*70}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{text.center(70)}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{'='*70}{Color.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Color.OKGREEN}✓ {text}{Color.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Color.FAIL}✗ {text}{Color.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Color.WARNING}⚠ {text}{Color.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Color.OKCYAN}ℹ {text}{Color.ENDC}")


def check_server():
    """Check if the server is running."""
    import requests
    
    try:
        response = requests.get(f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/v1/dashboard/health", timeout=5)
        if response.status_code == 200:
            return True
    except Exception:
        pass
    return False


def run_test_suite(name, test_file, markers=None):
    """Run a specific test suite."""
    print_header(f"Running {name}")
    
    cmd = ["pytest", f"tests/{test_file}", "-v", "--tb=short"]
    if markers:
        cmd.extend(["-m", markers])
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    # Parse output
    output = result.stdout + result.stderr
    
    # Count results
    passed = output.count(" PASSED")
    failed = output.count(" FAILED")
    skipped = output.count(" SKIPPED")
    
    print(f"\n{Color.BOLD}Results:{Color.ENDC}")
    print(f"  Passed:  {Color.OKGREEN}{passed}{Color.ENDC}")
    print(f"  Failed:  {Color.FAIL}{failed}{Color.ENDC}")
    print(f"  Skipped: {Color.WARNING}{skipped}{Color.ENDC}")
    print(f"  Time:    {elapsed:.2f}s")
    
    return {
        "name": name,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "elapsed": elapsed,
        "success": result.returncode == 0,
        "output": output
    }


def generate_report(results):
    """Generate test report."""
    print_header("Test Summary Report")
    
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_time = sum(r["elapsed"] for r in results)
    total_suites = len(results)
    passed_suites = sum(1 for r in results if r["success"])
    
    print(f"{Color.BOLD}Overall Statistics:{Color.ENDC}")
    print(f"  Test Suites: {passed_suites}/{total_suites} passed")
    print(f"  Total Tests: {total_passed + total_failed + total_skipped}")
    print(f"  Passed:      {Color.OKGREEN}{total_passed}{Color.ENDC}")
    print(f"  Failed:      {Color.FAIL}{total_failed}{Color.ENDC}")
    print(f"  Skipped:     {Color.WARNING}{total_skipped}{Color.ENDC}")
    print(f"  Total Time:  {total_time:.2f}s")
    
    print(f"\n{Color.BOLD}Suite Breakdown:{Color.ENDC}")
    for result in results:
        status = "✓" if result["success"] else "✗"
        color = Color.OKGREEN if result["success"] else Color.FAIL
        print(f"  {color}{status} {result['name']:<40} {result['elapsed']:>6.2f}s{Color.ENDC}")
    
    # Save detailed report
    report_dir = Path("tests/reports")
    report_dir.mkdir(exist_ok=True, parents=True)
    
    report_file = report_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "total_tests": total_passed + total_failed + total_skipped,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "total_time": total_time,
            },
            "suites": results
        }, f, indent=2)
    
    print(f"\n{Color.OKCYAN}Detailed report saved: {report_file}{Color.ENDC}")
    
    return total_failed == 0


def main():
    """Main test runner."""
    print_header("Dashboard E2E Test Suite")
    print_info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if server is running
    print_info("Checking if server is running...")
    if not check_server():
        print_error("Server is not running!")
        print_warning("Please start the server first:")
        print_warning("  uvicorn src.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    print_success("Server is running")
    
    # Run test suites
    results = []
    
    # 1. API Integration Tests
    results.append(run_test_suite(
        "API Integration Tests",
        "test_dashboard_api.py"
    ))
    
    # 2. HTML Validation Tests
    results.append(run_test_suite(
        "HTML Validation Tests",
        "test_dashboard_html.py"
    ))
    
    # 3. E2E Browser Tests
    results.append(run_test_suite(
        "E2E Browser Tests",
        "test_dashboard_e2e.py"
    ))
    
    # 4. Snapshot Tests
    results.append(run_test_suite(
        "Visual Snapshot Tests",
        "test_dashboard_snapshots.py"
    ))
    
    # Generate final report
    success = generate_report(results)
    
    # Check snapshots
    snapshot_dir = Path("tests/snapshots")
    if snapshot_dir.exists():
        snapshots = list(snapshot_dir.glob("*"))
        print_info(f"\nSnapshots created: {len(snapshots)}")
        print_info(f"Snapshot location: {snapshot_dir.absolute()}")
    
    # Final status
    print_header("Test Run Complete")
    if success:
        print_success("All tests passed! ✨")
        sys.exit(0)
    else:
        print_error("Some tests failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
