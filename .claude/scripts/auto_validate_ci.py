#!/usr/bin/env python3
"""
Automatic CI Validation Script

Detects modified services and runs appropriate validation checks.
This script should be automatically invoked after /speckit.implement completes.

Usage:
    python auto_validate_ci.py
    python auto_validate_ci.py --fix-auto
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Set


class Colors:
    """ANSI color codes (Windows compatible)"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class CIValidator:
    """Automatic CI validation orchestrator"""

    def __init__(self, fix_auto: bool = False, verbose: bool = False):
        self.fix_auto = fix_auto
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent.parent
        self.modified_services: Dict[str, Set[str]] = {"python": set(), "typescript": set()}
        self.validation_results: List[Dict] = []

    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title:^70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")

    def detect_modified_services(self) -> bool:
        """Detect modified services using git status"""
        print(f"{Colors.BOLD}[STEP 1]{Colors.RESET} Detecting modified services...\n")

        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            if result.returncode != 0:
                print(
                    f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run git status: {result.stderr}"
                )
                return False

            modified_files = result.stdout.strip().split("\n")

            # Service path patterns
            python_services = [
                "services/ecommerce/backend",
                "services/fds",
                "services/ml-service",
                "services/admin-dashboard/backend",
            ]

            typescript_services = [
                "services/ecommerce/frontend",
                "services/admin-dashboard/frontend",
            ]

            # Detect modified services
            for line in modified_files:
                if not line.strip():
                    continue

                # Extract file path (skip git status flags)
                parts = line.strip().split()
                if len(parts) < 2:
                    continue

                file_path = parts[1]

                # Check Python services
                for service in python_services:
                    if file_path.startswith(service):
                        self.modified_services["python"].add(service)
                        break

                # Check TypeScript services
                for service in typescript_services:
                    if file_path.startswith(service):
                        self.modified_services["typescript"].add(service)
                        break

            # Print detected services
            total_services = (
                len(self.modified_services["python"])
                + len(self.modified_services["typescript"])
            )

            if total_services == 0:
                print(
                    f"{Colors.YELLOW}[INFO]{Colors.RESET} No modified services detected."
                )
                print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} Nothing to validate.")
                return False

            print(f"{Colors.GREEN}[FOUND]{Colors.RESET} {total_services} modified services:\n")

            if self.modified_services["python"]:
                print(f"{Colors.BOLD}Python Services:{Colors.RESET}")
                for service in sorted(self.modified_services["python"]):
                    print(f"  - {service}")

            if self.modified_services["typescript"]:
                print(f"\n{Colors.BOLD}TypeScript Services:{Colors.RESET}")
                for service in sorted(self.modified_services["typescript"]):
                    print(f"  - {service}")

            return True

        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to detect services: {e}")
            return False

    def validate_python_service(self, service_path: str) -> bool:
        """Validate a Python service"""
        print(
            f"\n{Colors.BOLD}{Colors.BLUE}[Python]{Colors.RESET} Validating {service_path}...\n"
        )

        script_path = self.project_root / ".claude" / "scripts" / "validate_python_service.py"

        cmd = ["python", str(script_path), service_path]
        if self.verbose:
            cmd.append("-v")

        result = subprocess.run(cmd, cwd=self.project_root)

        self.validation_results.append(
            {"service": service_path, "type": "python", "passed": result.returncode == 0}
        )

        return result.returncode == 0

    def validate_typescript_service(self, service_path: str) -> bool:
        """Validate a TypeScript service"""
        print(
            f"\n{Colors.BOLD}{Colors.BLUE}[TypeScript]{Colors.RESET} Validating {service_path}...\n"
        )

        script_path = (
            self.project_root / ".claude" / "scripts" / "validate_typescript_service.py"
        )

        cmd = ["python", str(script_path), service_path]
        if self.verbose:
            cmd.append("-v")

        result = subprocess.run(cmd, cwd=self.project_root)

        self.validation_results.append(
            {
                "service": service_path,
                "type": "typescript",
                "passed": result.returncode == 0,
            }
        )

        return result.returncode == 0

    def run_validations(self) -> bool:
        """Run all validations"""
        self.print_header("CI VALIDATION")

        # Step 1: Detect services
        if not self.detect_modified_services():
            return True  # No services to validate

        # Step 2: Validate Python services
        if self.modified_services["python"]:
            print(
                f"\n{Colors.BOLD}[STEP 2]{Colors.RESET} Validating Python services...\n"
            )

            for service in sorted(self.modified_services["python"]):
                self.validate_python_service(service)

        # Step 3: Validate TypeScript services
        if self.modified_services["typescript"]:
            print(
                f"\n{Colors.BOLD}[STEP 3]{Colors.RESET} Validating TypeScript services...\n"
            )

            for service in sorted(self.modified_services["typescript"]):
                self.validate_typescript_service(service)

        # Step 4: Print summary
        return self.print_summary()

    def print_summary(self) -> bool:
        """Print validation summary"""
        self.print_header("VALIDATION SUMMARY")

        passed = sum(1 for r in self.validation_results if r["passed"])
        total = len(self.validation_results)

        # Print individual results
        for result in self.validation_results:
            status = (
                f"{Colors.GREEN}[PASS]{Colors.RESET}"
                if result["passed"]
                else f"{Colors.RED}[FAIL]{Colors.RESET}"
            )
            service_type = (
                f"{Colors.BLUE}[{result['type'].upper()}]{Colors.RESET}"
            )
            print(f"{status} {service_type} {result['service']}")

        # Print summary
        print(f"\n{Colors.BOLD}Total:{Colors.RESET} {passed}/{total} services passed\n")

        if passed == total:
            print(
                f"{Colors.GREEN}{Colors.BOLD}[SUCCESS]{Colors.RESET} All CI checks passed!"
            )
            print(f"{Colors.GREEN}[SAFE]{Colors.RESET} Ready to commit and push.\n")
            return True
        else:
            print(
                f"{Colors.RED}{Colors.BOLD}[FAILURE]{Colors.RESET} Some CI checks failed."
            )
            print(
                f"{Colors.YELLOW}[WARNING]{Colors.RESET} Fix issues before committing.\n"
            )
            return False

    def print_next_steps(self, success: bool):
        """Print next steps"""
        if success:
            print(f"{Colors.BOLD}Next Steps:{Colors.RESET}")
            print(f"  1. Review changes: git status")
            print(f"  2. Stage changes: git add .")
            print(f"  3. Commit: git commit -m 'your message'")
            print(f"  4. Push: git push\n")
        else:
            print(f"{Colors.BOLD}Next Steps:{Colors.RESET}")
            print(f"  1. Review failed checks above")
            print(f"  2. Fix issues (see fix suggestions)")
            print(f"  3. Run validation again: python .claude/scripts/auto_validate_ci.py")
            print(f"  4. Once all checks pass, commit and push\n")


def main():
    parser = argparse.ArgumentParser(description="Automatic CI validation")
    parser.add_argument(
        "--fix-auto",
        action="store_true",
        help="Automatically fix issues (Black, Ruff auto-fix)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    validator = CIValidator(fix_auto=args.fix_auto, verbose=args.verbose)

    try:
        success = validator.run_validations()
        validator.print_next_steps(success)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[ABORT]{Colors.RESET} Validation interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}[ERROR]{Colors.RESET} Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
