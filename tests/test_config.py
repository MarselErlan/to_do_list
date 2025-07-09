"""
Test configuration for Voice Assistant TDD with >90% coverage maintenance.
"""

import os
import json
import pytest
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class TestEnvironment(Enum):
    """Test environment types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class TestConfig:
    """Test configuration for different environments."""
    environment: TestEnvironment
    database_url: str
    google_credentials: Optional[str]
    coverage_threshold: float
    timeout_seconds: int
    parallel_workers: int
    mock_external_services: bool
    log_level: str
    
    @classmethod
    def get_unit_config(cls) -> 'TestConfig':
        """Get configuration for unit tests."""
        return cls(
            environment=TestEnvironment.UNIT,
            database_url="sqlite:///test_unit.db",
            google_credentials=None,
            coverage_threshold=95.0,
            timeout_seconds=30,
            parallel_workers=4,
            mock_external_services=True,
            log_level="ERROR"
        )
    
    @classmethod
    def get_integration_config(cls) -> 'TestConfig':
        """Get configuration for integration tests."""
        return cls(
            environment=TestEnvironment.INTEGRATION,
            database_url="sqlite:///test_integration.db",
            google_credentials=os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON"),
            coverage_threshold=85.0,
            timeout_seconds=120,
            parallel_workers=2,
            mock_external_services=False,
            log_level="INFO"
        )
    
    @classmethod
    def get_e2e_config(cls) -> 'TestConfig':
        """Get configuration for end-to-end tests."""
        return cls(
            environment=TestEnvironment.E2E,
            database_url="sqlite:///test_e2e.db",
            google_credentials=os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON"),
            coverage_threshold=90.0,
            timeout_seconds=300,
            parallel_workers=1,
            mock_external_services=False,
            log_level="DEBUG"
        )
    
    @classmethod
    def get_performance_config(cls) -> 'TestConfig':
        """Get configuration for performance tests."""
        return cls(
            environment=TestEnvironment.PERFORMANCE,
            database_url="sqlite:///test_performance.db",
            google_credentials=os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON"),
            coverage_threshold=80.0,
            timeout_seconds=600,
            parallel_workers=1,
            mock_external_services=False,
            log_level="WARNING"
        )


class CoverageMonitor:
    """Monitor and maintain test coverage above 90%."""
    
    def __init__(self, target_coverage: float = 90.0):
        self.target_coverage = target_coverage
        self.coverage_history = []
        self.coverage_file = "coverage_history.json"
        self.load_coverage_history()
    
    def load_coverage_history(self):
        """Load coverage history from file."""
        if os.path.exists(self.coverage_file):
            try:
                with open(self.coverage_file, 'r') as f:
                    self.coverage_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.coverage_history = []
    
    def save_coverage_history(self):
        """Save coverage history to file."""
        try:
            with open(self.coverage_file, 'w') as f:
                json.dump(self.coverage_history, f, indent=2)
        except IOError:
            print(f"Warning: Could not save coverage history to {self.coverage_file}")
    
    def record_coverage(self, coverage_percent: float, test_type: str, timestamp: str):
        """Record coverage result."""
        coverage_record = {
            "timestamp": timestamp,
            "coverage_percent": coverage_percent,
            "test_type": test_type,
            "target_met": coverage_percent >= self.target_coverage
        }
        
        self.coverage_history.append(coverage_record)
        
        # Keep only last 100 records
        if len(self.coverage_history) > 100:
            self.coverage_history = self.coverage_history[-100:]
        
        self.save_coverage_history()
    
    def get_coverage_trend(self, last_n_runs: int = 10) -> Dict[str, Any]:
        """Get coverage trend for last N runs."""
        if not self.coverage_history:
            return {"trend": "no_data", "average": 0.0, "meets_target": False}
        
        recent_runs = self.coverage_history[-last_n_runs:]
        
        if len(recent_runs) < 2:
            return {"trend": "insufficient_data", "average": 0.0, "meets_target": False}
        
        coverages = [run["coverage_percent"] for run in recent_runs]
        average_coverage = sum(coverages) / len(coverages)
        
        # Calculate trend
        first_half = coverages[:len(coverages)//2]
        second_half = coverages[len(coverages)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 1.0:
            trend = "improving"
        elif second_avg < first_avg - 1.0:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "average": average_coverage,
            "meets_target": average_coverage >= self.target_coverage,
            "recent_runs": len(recent_runs)
        }
    
    def get_coverage_report(self) -> str:
        """Generate coverage report."""
        if not self.coverage_history:
            return "No coverage history available."
        
        latest = self.coverage_history[-1]
        trend = self.get_coverage_trend()
        
        report = f"""
Voice Assistant Test Coverage Report
=====================================

Current Coverage: {latest['coverage_percent']:.1f}%
Target Coverage: {self.target_coverage:.1f}%
Status: {'✅ MEETS TARGET' if latest['target_met'] else '❌ BELOW TARGET'}

Trend Analysis (last 10 runs):
- Trend: {trend['trend'].upper()}
- Average: {trend['average']:.1f}%
- Meets Target: {'Yes' if trend['meets_target'] else 'No'}

Latest Test Run:
- Type: {latest['test_type']}
- Timestamp: {latest['timestamp']}
- Coverage: {latest['coverage_percent']:.1f}%

Recommendations:
"""
        
        if latest['coverage_percent'] < self.target_coverage:
            report += f"- Coverage is {self.target_coverage - latest['coverage_percent']:.1f}% below target\n"
            report += "- Add more unit tests for uncovered code paths\n"
            report += "- Review integration test scenarios\n"
            report += "- Consider edge cases and error handling\n"
        
        if trend['trend'] == 'declining':
            report += "- Coverage is declining - investigate recent changes\n"
            report += "- Ensure new features have comprehensive tests\n"
            report += "- Review deleted tests or refactored code\n"
        
        if trend['trend'] == 'improving':
            report += "- Coverage is improving - great job!\n"
            report += "- Continue adding comprehensive test scenarios\n"
        
        return report


class TestScenarioManager:
    """Manage realistic test scenarios for >90% coverage."""
    
    def __init__(self):
        self.scenarios = {
            "basic_functionality": [
                "test_voice_assistant_initialization",
                "test_service_configuration",
                "test_audio_processing_basic",
                "test_text_to_speech_basic"
            ],
            "user_scenarios": [
                "test_quick_task_creation",
                "test_unclear_request_handling",
                "test_complex_meeting_scheduling",
                "test_multiple_task_processing",
                "test_noisy_environment_handling"
            ],
            "error_handling": [
                "test_network_connectivity_issues",
                "test_invalid_audio_format",
                "test_service_unavailable",
                "test_authentication_failures",
                "test_malformed_input"
            ],
            "performance": [
                "test_high_load_processing",
                "test_large_audio_files",
                "test_response_time_limits",
                "test_memory_usage_optimization",
                "test_concurrent_requests"
            ],
            "security": [
                "test_input_sanitization",
                "test_authentication_requirements",
                "test_privacy_protection",
                "test_credential_validation",
                "test_secure_communication"
            ],
            "integration": [
                "test_real_google_cloud_services",
                "test_database_interactions",
                "test_langchain_integration",
                "test_end_to_end_workflows",
                "test_external_api_integration"
            ]
        }
    
    def get_missing_scenarios(self, completed_tests: List[str]) -> Dict[str, List[str]]:
        """Identify missing test scenarios for comprehensive coverage."""
        missing = {}
        
        for category, tests in self.scenarios.items():
            missing_tests = [test for test in tests if test not in completed_tests]
            if missing_tests:
                missing[category] = missing_tests
        
        return missing
    
    def get_scenario_coverage(self, completed_tests: List[str]) -> Dict[str, float]:
        """Calculate coverage percentage for each scenario category."""
        coverage = {}
        
        for category, tests in self.scenarios.items():
            completed_count = sum(1 for test in tests if test in completed_tests)
            coverage[category] = (completed_count / len(tests)) * 100
        
        return coverage
    
    def generate_scenario_report(self, completed_tests: List[str]) -> str:
        """Generate comprehensive scenario coverage report."""
        missing = self.get_missing_scenarios(completed_tests)
        coverage = self.get_scenario_coverage(completed_tests)
        
        report = """
Voice Assistant Test Scenario Coverage
======================================

"""
        
        for category, percentage in coverage.items():
            status = "✅" if percentage >= 90 else "⚠️" if percentage >= 70 else "❌"
            report += f"{status} {category.replace('_', ' ').title()}: {percentage:.1f}%\n"
        
        if missing:
            report += "\nMissing Test Scenarios:\n"
            report += "-" * 25 + "\n"
            
            for category, tests in missing.items():
                report += f"\n{category.replace('_', ' ').title()}:\n"
                for test in tests:
                    report += f"  - {test}\n"
        
        overall_coverage = sum(coverage.values()) / len(coverage)
        report += f"\nOverall Scenario Coverage: {overall_coverage:.1f}%\n"
        
        if overall_coverage < 90:
            report += f"\nNeed {90 - overall_coverage:.1f}% more coverage to reach 90% target.\n"
        
        return report


# Test markers for different test types
pytest_markers = {
    "unit": "pytest.mark.unit",
    "integration": "pytest.mark.integration", 
    "e2e": "pytest.mark.e2e",
    "performance": "pytest.mark.performance",
    "security": "pytest.mark.security",
    "slow": "pytest.mark.slow"
}


def get_test_config(test_type: str) -> TestConfig:
    """Get test configuration based on test type."""
    configs = {
        "unit": TestConfig.get_unit_config(),
        "integration": TestConfig.get_integration_config(),
        "e2e": TestConfig.get_e2e_config(),
        "performance": TestConfig.get_performance_config()
    }
    
    return configs.get(test_type, TestConfig.get_unit_config())


def setup_test_environment(config: TestConfig):
    """Setup test environment based on configuration."""
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["TEST_DATABASE_URL"] = config.database_url
    os.environ["LOG_LEVEL"] = config.log_level
    
    if config.google_credentials:
        os.environ["GOOGLE_CLOUD_CREDENTIALS_JSON"] = config.google_credentials
    
    # Configure mock settings
    if config.mock_external_services:
        os.environ["MOCK_EXTERNAL_SERVICES"] = "true"
    
    # Setup database
    if config.database_url.startswith("sqlite"):
        db_file = config.database_url.replace("sqlite:///", "")
        if os.path.exists(db_file):
            os.remove(db_file)


# Global test configuration
current_test_config = None


@pytest.fixture(scope="session")
def test_config():
    """Global test configuration fixture."""
    global current_test_config
    
    test_type = os.environ.get("TEST_TYPE", "unit")
    current_test_config = get_test_config(test_type)
    setup_test_environment(current_test_config)
    
    return current_test_config


@pytest.fixture(scope="session")  
def coverage_monitor():
    """Global coverage monitor fixture."""
    return CoverageMonitor(target_coverage=90.0)


@pytest.fixture(scope="session")
def scenario_manager():
    """Global scenario manager fixture."""
    return TestScenarioManager()


# Custom pytest plugin for coverage tracking
class CoveragePlugin:
    """Custom pytest plugin for real-time coverage tracking."""
    
    def __init__(self):
        self.coverage_monitor = CoverageMonitor()
        self.scenario_manager = TestScenarioManager()
    
    def pytest_runtest_logreport(self, report):
        """Track test results for coverage analysis."""
        if report.when == "call":
            # Track completed tests
            test_name = report.nodeid.split("::")[-1]
            if report.outcome == "passed":
                print(f"✅ {test_name}")
            elif report.outcome == "failed":
                print(f"❌ {test_name}")
            elif report.outcome == "skipped":
                print(f"⏭️ {test_name}")
    
    def pytest_sessionfinish(self, session, exitstatus):
        """Generate coverage report at session end."""
        if hasattr(session, 'coverage'):
            # This would integrate with pytest-cov
            pass


if __name__ == "__main__":
    # Example usage
    monitor = CoverageMonitor()
    manager = TestScenarioManager()
    
    # Simulate some test results
    import datetime
    now = datetime.datetime.now().isoformat()
    
    monitor.record_coverage(92.5, "unit", now)
    print(monitor.get_coverage_report())
    
    completed_tests = [
        "test_voice_assistant_initialization",
        "test_service_configuration",
        "test_quick_task_creation",
        "test_network_connectivity_issues",
        "test_high_load_processing",
        "test_input_sanitization",
        "test_real_google_cloud_services"
    ]
    
    print(manager.generate_scenario_report(completed_tests)) 