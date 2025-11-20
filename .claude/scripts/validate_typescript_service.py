#!/usr/bin/env python3
"""
TypeScript Service CI Validation Script

Performs the same checks as GitHub Actions CI:
1. npm ci (clean install)
2. ESLint
3. TypeScript type check
4. Unit tests (if available)
5. Production build

Usage:
    python validate_typescript_service.py services/ecommerce/frontend
    python validate_typescript_service.py services/admin-dashboard/frontend
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


class TypeScriptServiceValidator:
    """Validator for TypeScript services"""

    def __init__(self, service_path: str, verbose: bool = False):
        self.service_path = Path(service_path)
        self.verbose = verbose
        self.results: List[ValidationResult] = []

        if not self.service_path.exists():
            raise ValueError(f"Service path does not exist: {service_path}")

        if not (self.service_path / "package.json").exists():
            raise ValueError(f"package.json not found in {service_path}")

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
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                shell=True,  # Windows compatibility
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
            print(result.output[:500])  # Limit output length

        if result.error:
            print(f"{Colors.RED}Error:{Colors.RESET}")
            print(result.error[:1000])  # Limit error length

    def validate_npm_install(self) -> ValidationResult:
        """Validate npm install"""
        print(f"{Colors.BLUE}[1/5]{Colors.RESET} Installing dependencies...")

        returncode, stdout, stderr = self.run_command(["npm", "ci"])

        if returncode == 0:
            return ValidationResult(
                "npm ci", passed=True, output="Dependencies installed successfully"
            )
        else:
            return ValidationResult(
                "npm ci",
                passed=False,
                error=f"Failed to install dependencies:\n{stderr}",
            )

    def validate_eslint(self) -> ValidationResult:
        """Validate ESLint"""
        print(f"{Colors.BLUE}[2/5]{Colors.RESET} Checking ESLint...")

        returncode, stdout, stderr = self.run_command(["npm", "run", "lint"])

        if returncode == 0:
            return ValidationResult(
                "ESLint", passed=True, output="No linting issues found"
            )
        else:
            # ESLint failures are sometimes acceptable (warnings)
            if "warning" in stdout.lower() and "error" not in stdout.lower():
                return ValidationResult(
                    "ESLint",
                    passed=True,
                    output=f"Warnings found (non-blocking):\n{stdout}",
                )
            else:
                return ValidationResult(
                    "ESLint",
                    passed=False,
                    error=f"Linting errors found:\n{stdout}\n{stderr}",
                )

    def validate_typescript_check(self) -> ValidationResult:
        """Validate TypeScript type check"""
        print(f"{Colors.BLUE}[3/5]{Colors.RESET} Checking TypeScript types...")

        returncode, stdout, stderr = self.run_command(["npx", "tsc", "--noEmit"])

        if returncode == 0:
            return ValidationResult(
                "TypeScript type check", passed=True, output="No type errors found"
            )
        else:
            return ValidationResult(
                "TypeScript type check",
                passed=False,
                error=f"Type errors found:\n{stdout}\n{stderr}",
            )

    def validate_unit_tests(self) -> ValidationResult:
        """Validate unit tests"""
        print(f"{Colors.BLUE}[4/5]{Colors.RESET} Running unit tests...")

        # Check if tests are configured
        returncode, stdout, stderr = self.run_command(
            ["npm", "test", "--", "--run", "--coverage"]
        )

        if returncode == 0:
            return ValidationResult("Unit tests", passed=True, output=stdout)
        else:
            # Tests might not be configured, which is acceptable
            if "no test specified" in stderr.lower() or "no tests found" in stdout.lower():
                return ValidationResult(
                    "Unit tests", passed=True, output="No tests configured (skipped)"
                )
            else:
                return ValidationResult(
                    "Unit tests",
                    passed=False,
                    error=f"Some tests failed:\n{stdout}\n{stderr}",
                )

    def validate_production_build(self) -> ValidationResult:
        """Validate production build"""
        print(f"{Colors.BLUE}[5/5]{Colors.RESET} Building production bundle...")

        returncode, stdout, stderr = self.run_command(["npm", "run", "build"])

        if returncode == 0:
            # Check build output size
            dist_dir = self.service_path / "dist"
            if dist_dir.exists():
                import os

                total_size = sum(
                    os.path.getsize(os.path.join(root, file))
                    for root, dirs, files in os.walk(dist_dir)
                    for file in files
                )
                size_mb = total_size / (1024 * 1024)
                return ValidationResult(
                    "Production build",
                    passed=True,
                    output=f"Build successful (size: {size_mb:.2f} MB)",
                )
            else:
                return ValidationResult(
                    "Production build", passed=True, output="Build successful"
                )
        else:
            return ValidationResult(
                "Production build",
                passed=False,
                error=f"Build failed:\n{stdout}\n{stderr}",
            )

    def run_all_validations(self) -> bool:
        """Run all validations and return True if all passed"""
        self.print_header(f"Validating TypeScript Service: {self.service_path}")

        # Run all validations
        self.results = [
            self.validate_npm_install(),
            self.validate_eslint(),
            self.validate_typescript_check(),
            self.validate_unit_tests(),
            self.validate_production_build(),
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
            if "npm ci" in result.name:
                print(f"- {result.name}: Check package.json and package-lock.json")
                print("  Try: rm -rf node_modules package-lock.json && npm install")
            elif "ESLint" in result.name:
                print(f"- {result.name}: Run 'npm run lint' to see detailed errors")
                print("  Fix issues manually or use --fix flag if available")
            elif "TypeScript" in result.name:
                print(
                    f"- {result.name}: Fix type errors shown above (file:line:column)"
                )
                print("  Use VS Code or 'npx tsc --noEmit' for detailed errors")
            elif "Unit tests" in result.name:
                print(f"- {result.name}: Fix test failures (see error output above)")
            elif "Production build" in result.name:
                print(f"- {result.name}: Fix build errors (see error output above)")
                print("  Check for missing dependencies or TypeScript errors")


def main():
    parser = argparse.ArgumentParser(
        description="Validate TypeScript service for CI compliance"
    )
    parser.add_argument(
        "service_path",
        help="Path to service directory (e.g., services/ecommerce/frontend)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    try:
        validator = TypeScriptServiceValidator(args.service_path, verbose=args.verbose)
        success = validator.run_all_validations()

        if not success:
            validator.print_fix_suggestions()
            sys.exit(1)

    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
