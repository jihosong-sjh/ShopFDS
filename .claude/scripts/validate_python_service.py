#!/usr/bin/env python3
"""
Python Service CI Validation Script

Performs the same checks as GitHub Actions CI:
1. Black formatting
2. Ruff linting
3. pytest unit tests
4. pytest integration tests
5. pytest performance tests (FDS only)
6. Dependencies check

Usage:
    python validate_python_service.py services/ecommerce/backend
    python validate_python_service.py services/fds
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes (Windows compatible)"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class ValidationResult:
    """Result of a validation check"""

    def __init__(self, name: str, passed: bool, output: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.output = output
        self.error = error


class PythonServiceValidator:
    """Validator for Python services"""

    def __init__(self, service_path: str, verbose: bool = False):
        self.service_path = Path(service_path)
        self.verbose = verbose
        self.results: List[ValidationResult] = []

        if not self.service_path.exists():
            raise ValueError(f"Service path does not exist: {service_path}")

        if not (self.service_path / "src").exists():
            raise ValueError(f"src/ directory not found in {service_path}")

    def run_command(
        self, cmd: List[str], cwd: Path = None, check: bool = False
    ) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)"""
        if cwd is None:
            cwd = self.service_path

        if self.verbose:
            print(f"{Colors.BLUE}[CMD]{Colors.RESET} {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8"
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    def print_result(self, result: ValidationResult):
        """Print validation result"""
        if result.passed:
            status = f"{Colors.GREEN}[OK]{Colors.RESET}"
        else:
            status = f"{Colors.RED}[FAIL]{Colors.RESET}"

        print(f"{status} {result.name}")

        if self.verbose and result.output:
            print(f"{Colors.YELLOW}Output:{Colors.RESET}")
            print(result.output)

        if result.error:
            print(f"{Colors.RED}Error:{Colors.RESET}")
            print(result.error)

    def validate_black_formatting(self) -> ValidationResult:
        """Validate Black formatting"""
        print(f"{Colors.BLUE}[1/6]{Colors.RESET} Checking Black formatting...")

        # First, apply formatting
        returncode, stdout, stderr = self.run_command(["black", "src/"])

        # Then, check if code is formatted
        returncode, stdout, stderr = self.run_command(["black", "--check", "src/"])

        if returncode == 0:
            return ValidationResult(
                "Black formatting", passed=True, output="All files formatted correctly"
            )
        else:
            return ValidationResult(
                "Black formatting",
                passed=False,
                error=f"Some files need formatting:\n{stderr}",
            )

    def validate_ruff_linting(self) -> ValidationResult:
        """Validate Ruff linting"""
        print(f"{Colors.BLUE}[2/6]{Colors.RESET} Checking Ruff linting...")

        # First, auto-fix issues
        returncode, stdout, stderr = self.run_command(
            ["ruff", "check", "src/", "--fix"]
        )

        # Then, check for remaining issues
        returncode, stdout, stderr = self.run_command(["ruff", "check", "src/"])

        if returncode == 0:
            return ValidationResult(
                "Ruff linting", passed=True, output="No linting issues found"
            )
        else:
            return ValidationResult(
                "Ruff linting",
                passed=False,
                error=f"Linting issues found:\n{stdout}\n{stderr}",
            )

    def validate_unit_tests(self) -> ValidationResult:
        """Validate unit tests"""
        print(f"{Colors.BLUE}[3/6]{Colors.RESET} Running unit tests...")

        returncode, stdout, stderr = self.run_command(
            ["pytest", "tests/unit", "-v", "--cov=src", "--cov-report=term"]
        )

        if returncode == 0:
            # Extract coverage percentage
            coverage_line = [
                line for line in stdout.split("\n") if "TOTAL" in line and "%" in line
            ]
            coverage = (
                coverage_line[0].strip() if coverage_line else "Coverage not found"
            )

            return ValidationResult(
                "Unit tests", passed=True, output=f"All tests passed\n{coverage}"
            )
        else:
            return ValidationResult(
                "Unit tests",
                passed=False,
                error=f"Some tests failed:\n{stdout}\n{stderr}",
            )

    def validate_integration_tests(self) -> ValidationResult:
        """Validate integration tests"""
        print(f"{Colors.BLUE}[4/6]{Colors.RESET} Running integration tests...")

        # Check if integration tests exist
        if not (self.service_path / "tests" / "integration").exists():
            return ValidationResult(
                "Integration tests",
                passed=True,
                output="No integration tests found (skipped)",
            )

        returncode, stdout, stderr = self.run_command(
            ["pytest", "tests/integration", "-v"]
        )

        if returncode == 0:
            return ValidationResult("Integration tests", passed=True, output=stdout)
        else:
            return ValidationResult(
                "Integration tests",
                passed=False,
                error=f"Some tests failed:\n{stdout}\n{stderr}",
            )

    def validate_performance_tests(self) -> ValidationResult:
        """Validate performance tests (FDS only)"""
        print(
            f"{Colors.BLUE}[5/6]{Colors.RESET} Running performance tests (FDS only)..."
        )

        # Check if this is FDS service
        if "fds" not in str(self.service_path).lower():
            return ValidationResult(
                "Performance tests",
                passed=True,
                output="Not FDS service (skipped)",
            )

        # Check if performance tests exist
        if not (self.service_path / "tests" / "performance").exists():
            return ValidationResult(
                "Performance tests",
                passed=True,
                output="No performance tests found (skipped)",
            )

        returncode, stdout, stderr = self.run_command(
            ["pytest", "tests/performance", "-v", "--benchmark-only"]
        )

        if returncode == 0:
            return ValidationResult("Performance tests", passed=True, output=stdout)
        else:
            return ValidationResult(
                "Performance tests",
                passed=False,
                error=f"Performance tests failed:\n{stdout}\n{stderr}",
            )

    def validate_dependencies(self) -> ValidationResult:
        """Validate dependencies"""
        print(f"{Colors.BLUE}[6/6]{Colors.RESET} Checking dependencies...")

        returncode, stdout, stderr = self.run_command(["pip", "check"])

        if returncode == 0:
            return ValidationResult(
                "Dependencies check", passed=True, output="No dependency conflicts"
            )
        else:
            return ValidationResult(
                "Dependencies check",
                passed=False,
                error=f"Dependency conflicts found:\n{stdout}\n{stderr}",
            )

    def run_all_validations(self) -> bool:
        """Run all validations and return True if all passed"""
        self.print_header(f"Validating Python Service: {self.service_path}")

        # Run all validations
        self.results = [
            self.validate_black_formatting(),
            self.validate_ruff_linting(),
            self.validate_unit_tests(),
            self.validate_integration_tests(),
            self.validate_performance_tests(),
            self.validate_dependencies(),
        ]

        # Print results
        print(f"\n{Colors.BOLD}Validation Results:{Colors.RESET}\n")
        for result in self.results:
            self.print_result(result)

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"Passed: {passed}/{total}")

        if passed == total:
            print(
                f"{Colors.GREEN}{Colors.BOLD}[SUCCESS]{Colors.RESET} All checks passed!"
            )
            return True
        else:
            print(
                f"{Colors.RED}{Colors.BOLD}[FAILURE]{Colors.RESET} Some checks failed."
            )
            return False

    def print_fix_suggestions(self):
        """Print suggestions for fixing failed checks"""
        failed = [r for r in self.results if not r.passed]

        if not failed:
            return

        print(f"\n{Colors.BOLD}{Colors.YELLOW}Fix Suggestions:{Colors.RESET}\n")

        for result in failed:
            if "Black" in result.name:
                print(f"- {result.name}: Run 'black src/' to auto-format")
            elif "Ruff" in result.name:
                print(f"- {result.name}: Run 'ruff check src/ --fix' to auto-fix")
            elif "Unit tests" in result.name or "Integration tests" in result.name:
                print(f"- {result.name}: Fix test failures (see error output above)")
            elif "Performance" in result.name:
                print(
                    f"- {result.name}: Optimize FDS engine to meet 100ms P95 target"
                )
            elif "Dependencies" in result.name:
                print(
                    f"- {result.name}: Resolve dependency conflicts with 'pip install --upgrade <package>'"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Validate Python service for CI compliance"
    )
    parser.add_argument(
        "service_path", help="Path to service directory (e.g., services/ecommerce/backend)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    args = parser.parse_args()

    try:
        validator = PythonServiceValidator(args.service_path, verbose=args.verbose)
        success = validator.run_all_validations()

        if not success:
            validator.print_fix_suggestions()
            sys.exit(1)

    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
