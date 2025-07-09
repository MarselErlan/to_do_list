#!/usr/bin/env python3
"""
Comprehensive Voice Assistant Test Runner with >90% Coverage Maintenance
========================================================================

This script runs all voice assistant tests with comprehensive coverage tracking
and maintains >90% test coverage for production readiness.
"""

import os
import sys
import subprocess
import json
import time
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tests.test_config import (
        TestConfig, CoverageMonitor, TestScenarioManager, 
        get_test_config, setup_test_environment
    )
except ImportError:
    print("Warning: Could not import test configuration. Running with basic setup.")
    TestConfig = None
    CoverageMonitor = None
    TestScenarioManager = None


@dataclass
class TestResult:
    """Test execution result."""
    test_type: str
    passed: int
    failed: int
    skipped: int
    total: int
    duration: float
    coverage_percent: float
    exit_code: int
    output: str


class ComprehensiveTestRunner:
    """Comprehensive test runner for voice assistant with coverage tracking."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results: List[TestResult] = []
        self.coverage_monitor = CoverageMonitor() if CoverageMonitor else None
        self.scenario_manager = TestScenarioManager() if TestScenarioManager else None
        self.target_coverage = 90.0
        
        # Test configurations
        self.test_suites = {
            "unit": {
                "path": "tests/unit/test_voice_assistant.py",
                "markers": "-m 'not slow'",
                "timeout": 300,
                "description": "Unit tests with mocked dependencies"
            },
            "scenarios": {
                "path": "tests/unit/test_voice_assistant_scenarios.py", 
                "markers": "-m 'not slow'",
                "timeout": 300,
                "description": "Realistic user scenario tests"
            },
            "integration": {
                "path": "tests/integration/test_voice_assistant_real_services.py",
                "markers": "-m 'not slow'",
                "timeout": 600,
                "description": "Integration tests with real Google Cloud services"
            },
            "performance": {
                "path": "tests/integration/test_voice_assistant_real_services.py",
                "markers": "-m 'slow'",
                "timeout": 1200,
                "description": "Performance and load tests"
            },
            "enhanced": {
                "path": "tests/unit/test_voice_assistant_enhanced.py",
                "markers": "",
                "timeout": 300,
                "description": "Enhanced comprehensive tests"
            }
        }
    
    def setup_environment(self, test_type: str):
        """Setup test environment for specific test type."""
        if TestConfig:
            config = get_test_config(test_type)
            setup_test_environment(config)
        else:
            # Basic setup without test_config
            os.environ["TESTING"] = "true"
            os.environ["TEST_TYPE"] = test_type
            os.environ["LOG_LEVEL"] = "ERROR"
    
    def run_test_suite(self, suite_name: str, verbose: bool = True) -> TestResult:
        """Run a specific test suite with coverage tracking."""
        suite_config = self.test_suites.get(suite_name)
        if not suite_config:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        self.setup_environment(suite_name)
        
        # Check if test file exists
        test_path = self.project_root / suite_config["path"]
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_path}")
            return TestResult(
                test_type=suite_name,
                passed=0, failed=0, skipped=1, total=1,
                duration=0.0, coverage_percent=0.0,
                exit_code=1, output=f"Test file not found: {test_path}"
            )
        
        print(f"\n🧪 Running {suite_name} tests...")
        print(f"📄 Description: {suite_config['description']}")
        print(f"📁 Path: {suite_config['path']}")
        print("-" * 80)
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "--tb=short",
            "--maxfail=5",
            f"--timeout={suite_config['timeout']}",
            "--cov=app.voice_assistant",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "-v" if verbose else "-q"
        ]
        
        # Add markers if specified
        if suite_config["markers"]:
            cmd.extend(suite_config["markers"].split())
        
        start_time = time.time()
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite_config["timeout"],
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            # Parse test output
            output_lines = result.stdout.split('\n')
            
            # Extract test counts
            passed = failed = skipped = total = 0
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Parse line like "5 passed, 2 failed, 1 skipped"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            passed = int(parts[i-1])
                        elif part == "failed" and i > 0:
                            failed = int(parts[i-1])
                        elif part == "skipped" and i > 0:
                            skipped = int(parts[i-1])
                elif line.strip().startswith("=") and "passed" in line:
                    # Parse line like "== 5 passed in 2.34s =="
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            passed = int(parts[i-1])
            
            total = passed + failed + skipped
            
            # Extract coverage percentage
            coverage_percent = 0.0
            if os.path.exists("coverage.json"):
                try:
                    with open("coverage.json", "r") as f:
                        coverage_data = json.load(f)
                        if "totals" in coverage_data:
                            coverage_percent = coverage_data["totals"]["percent_covered"]
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Create result
            test_result = TestResult(
                test_type=suite_name,
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=total,
                duration=duration,
                coverage_percent=coverage_percent,
                exit_code=result.returncode,
                output=result.stdout + "\n" + result.stderr
            )
            
            # Record coverage
            if self.coverage_monitor and coverage_percent > 0:
                timestamp = datetime.datetime.now().isoformat()
                self.coverage_monitor.record_coverage(
                    coverage_percent, suite_name, timestamp
                )
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                test_type=suite_name,
                passed=0, failed=1, skipped=0, total=1,
                duration=duration, coverage_percent=0.0,
                exit_code=124, output=f"Test timed out after {suite_config['timeout']} seconds"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_type=suite_name,
                passed=0, failed=1, skipped=0, total=1,
                duration=duration, coverage_percent=0.0,
                exit_code=1, output=f"Test execution failed: {str(e)}"
            )
    
    def run_all_tests(self, include_slow: bool = False) -> Dict[str, TestResult]:
        """Run all test suites and return comprehensive results."""
        print("=" * 80)
        print("🎯 COMPREHENSIVE VOICE ASSISTANT TEST SUITE")
        print("=" * 80)
        print(f"📅 Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target Coverage: {self.target_coverage}%")
        print()
        
        results = {}
        
        # Run test suites in order
        suite_order = ["unit", "scenarios", "enhanced", "integration"]
        if include_slow:
            suite_order.append("performance")
        
        for suite_name in suite_order:
            if suite_name not in self.test_suites:
                continue
                
            try:
                result = self.run_test_suite(suite_name, verbose=True)
                results[suite_name] = result
                self.test_results.append(result)
                
                # Print immediate results
                self.print_suite_summary(result)
                
            except Exception as e:
                print(f"❌ Error running {suite_name} tests: {str(e)}")
                continue
        
        return results
    
    def print_suite_summary(self, result: TestResult):
        """Print summary for a single test suite."""
        status = "✅ PASSED" if result.exit_code == 0 else "❌ FAILED"
        coverage_status = "✅" if result.coverage_percent >= self.target_coverage else "⚠️"
        
        print(f"\n{status} {result.test_type.upper()} Tests")
        print(f"  📊 Results: {result.passed} passed, {result.failed} failed, {result.skipped} skipped")
        print(f"  ⏱️  Duration: {result.duration:.2f}s")
        print(f"  {coverage_status} Coverage: {result.coverage_percent:.1f}%")
        
        if result.failed > 0:
            print(f"  ❌ Some tests failed - check output above")
        
        if result.coverage_percent < self.target_coverage:
            print(f"  ⚠️  Coverage below target ({self.target_coverage}%)")
    
    def generate_comprehensive_report(self, results: Dict[str, TestResult]) -> str:
        """Generate comprehensive test report."""
        if not results:
            return "No test results available."
        
        # Calculate totals
        total_passed = sum(r.passed for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        total_skipped = sum(r.skipped for r in results.values())
        total_tests = total_passed + total_failed + total_skipped
        total_duration = sum(r.duration for r in results.values())
        
        # Calculate overall coverage (weighted average)
        coverages = [(r.coverage_percent, r.total) for r in results.values() if r.coverage_percent > 0]
        if coverages:
            weighted_coverage = sum(c * w for c, w in coverages) / sum(w for _, w in coverages)
        else:
            weighted_coverage = 0.0
        
        # Generate report
        report = f"""
🎯 COMPREHENSIVE VOICE ASSISTANT TEST REPORT
={'=' * 60}

📅 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏱️  Total Duration: {total_duration:.2f}s

📊 OVERALL RESULTS
{'-' * 20}
✅ Total Passed: {total_passed}
❌ Total Failed: {total_failed}
⏭️  Total Skipped: {total_skipped}
📈 Total Tests: {total_tests}

🎯 COVERAGE ANALYSIS
{'-' * 20}
📊 Overall Coverage: {weighted_coverage:.1f}%
🎯 Target Coverage: {self.target_coverage}%
{'✅ MEETS TARGET' if weighted_coverage >= self.target_coverage else '❌ BELOW TARGET'}

📋 DETAILED RESULTS BY SUITE
{'-' * 30}
"""
        
        for suite_name, result in results.items():
            status = "✅ PASSED" if result.exit_code == 0 else "❌ FAILED"
            coverage_status = "✅" if result.coverage_percent >= self.target_coverage else "⚠️"
            
            report += f"""
{status} {suite_name.upper()} Tests
  📊 Results: {result.passed} passed, {result.failed} failed, {result.skipped} skipped
  ⏱️  Duration: {result.duration:.2f}s
  {coverage_status} Coverage: {result.coverage_percent:.1f}%
  📝 Description: {self.test_suites[suite_name]['description']}
"""
        
        # Add coverage trend analysis
        if self.coverage_monitor:
            trend = self.coverage_monitor.get_coverage_trend()
            report += f"""
📈 COVERAGE TREND ANALYSIS
{'-' * 25}
📊 Trend: {trend['trend'].upper()}
📈 Average (last 10 runs): {trend['average']:.1f}%
✅ Meets Target: {'Yes' if trend['meets_target'] else 'No'}
"""
        
        # Add scenario analysis
        if self.scenario_manager:
            # Get completed tests from results
            completed_tests = []
            for result in results.values():
                if result.passed > 0:
                    # This is a simplified approach - in practice, we'd parse test names
                    if "unit" in result.test_type:
                        completed_tests.extend([
                            "test_voice_assistant_initialization",
                            "test_service_configuration",
                            "test_audio_processing_basic"
                        ])
                    elif "scenarios" in result.test_type:
                        completed_tests.extend([
                            "test_quick_task_creation",
                            "test_unclear_request_handling",
                            "test_complex_meeting_scheduling"
                        ])
                    elif "integration" in result.test_type:
                        completed_tests.extend([
                            "test_real_google_cloud_services",
                            "test_database_interactions"
                        ])
            
            scenario_report = self.scenario_manager.generate_scenario_report(completed_tests)
            report += f"\n{scenario_report}"
        
        # Add recommendations
        report += f"""
🔧 RECOMMENDATIONS
{'-' * 18}
"""
        
        if weighted_coverage < self.target_coverage:
            gap = self.target_coverage - weighted_coverage
            report += f"📊 Coverage is {gap:.1f}% below target:\n"
            report += "  • Add more unit tests for edge cases\n"
            report += "  • Implement missing scenario tests\n"
            report += "  • Review error handling paths\n"
            report += "  • Add integration test cases\n"
        
        if total_failed > 0:
            report += f"❌ {total_failed} tests failed:\n"
            report += "  • Review failing test output above\n"
            report += "  • Fix implementation issues\n"
            report += "  • Update tests if requirements changed\n"
        
        if weighted_coverage >= self.target_coverage and total_failed == 0:
            report += "✅ Excellent test coverage and all tests passing!\n"
            report += "  • Maintain current test quality\n"
            report += "  • Continue adding tests for new features\n"
            report += "  • Consider adding more integration tests\n"
        
        return report
    
    def run_with_coverage_check(self, include_slow: bool = False) -> bool:
        """Run tests and ensure coverage meets target."""
        results = self.run_all_tests(include_slow=include_slow)
        
        # Generate and print report
        report = self.generate_comprehensive_report(results)
        print(report)
        
        # Check if we meet requirements
        total_failed = sum(r.failed for r in results.values())
        coverages = [r.coverage_percent for r in results.values() if r.coverage_percent > 0]
        
        if coverages:
            weighted_coverage = sum(coverages) / len(coverages)
            meets_coverage = weighted_coverage >= self.target_coverage
        else:
            meets_coverage = False
        
        success = total_failed == 0 and meets_coverage
        
        if success:
            print("\n🎉 SUCCESS: All tests passed and coverage target met!")
        else:
            print(f"\n❌ FAILURE: {'Tests failed' if total_failed > 0 else 'Coverage below target'}")
        
        return success


def main():
    """Main entry point for comprehensive test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Voice Assistant Test Runner")
    parser.add_argument("--suite", choices=["unit", "scenarios", "integration", "performance", "enhanced"], 
                       help="Run specific test suite")
    parser.add_argument("--include-slow", action="store_true", help="Include slow/performance tests")
    parser.add_argument("--coverage-only", action="store_true", help="Only run coverage check")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    if args.coverage_only:
        # Just generate coverage report
        if runner.coverage_monitor:
            print(runner.coverage_monitor.get_coverage_report())
        return
    
    if args.suite:
        # Run specific suite
        result = runner.run_test_suite(args.suite, verbose=args.verbose)
        runner.print_suite_summary(result)
        return result.exit_code == 0
    
    # Run comprehensive test suite
    success = runner.run_with_coverage_check(include_slow=args.include_slow)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 