"""
run_all_tests.py - A comprehensive test runner script with detailed output
"""

import os
import sys
import subprocess
import argparse
import time
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output
init()

def setup_env():
    """Setup the environment for testing."""
    print(f"{Fore.BLUE}Setting up test environment...{Style.RESET_ALL}")
    
    # Install test dependencies
    print("Installing test dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"], 
                   capture_output=True)
    
    # Make sure regular requirements are installed too
    print("Installing regular requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                   capture_output=True)
    
    # Additional requirements for the test runner
    print("Installing colorama for test output...")
    subprocess.run([sys.executable, "-m", "pip", "install", "colorama"],
                   capture_output=True)
    
    print(f"{Fore.GREEN}Environment setup complete!{Style.RESET_ALL}")

def run_tests(coverage=False, verbose=False, pattern=None, stop_on_failure=False):
    """Run the tests with the specified options."""
    print(f"{Fore.BLUE}Running tests...{Style.RESET_ALL}")
    
    # Build the pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add pattern filter if provided
    if pattern:
        cmd.append(pattern)
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term", "--cov-report=html"])
    
    if stop_on_failure:
        cmd.append("-x")
    
    # Add output formatting
    cmd.append("--no-header")
    cmd.append("-v")
    
    # Run the tests
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_time = time.time() - start_time
    
    # Display results
    print(f"\n{Fore.YELLOW}Test Output:{Style.RESET_ALL}")
    
    # Process and colorize the output
    if result.stdout:
        for line in result.stdout.splitlines():
            if "PASSED" in line:
                print(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
            elif "FAILED" in line:
                print(f"{Fore.RED}{line}{Style.RESET_ALL}")
            elif "SKIPPED" in line or "XFAIL" in line:
                print(f"{Fore.YELLOW}{line}{Style.RESET_ALL}")
            elif "ERROR" in line:
                print(f"{Fore.RED}{line}{Style.RESET_ALL}")
            else:
                print(line)
    
    # Print errors separately for better visibility
    if result.returncode != 0 and result.stderr:
        print(f"\n{Fore.RED}Errors:{Style.RESET_ALL}")
        print(result.stderr)
    
    # Print summary
    if result.returncode == 0:
        print(f"\n{Fore.GREEN}✅ All tests passed in {elapsed_time:.2f} seconds!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ Some tests failed. Execution time: {elapsed_time:.2f} seconds.{Style.RESET_ALL}")
    
    return result.returncode

def print_header():
    """Print a formatted header for the test run."""
    header = """
┌─────────────────────────────────────┐
│ WhatsApp Python Chatbot Test Runner │
└─────────────────────────────────────┘
"""
    print(f"{Fore.CYAN}{header}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Run tests for the WhatsApp chatbot")
    parser.add_argument("--setup", action="store_true", help="Setup the test environment")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--pattern", help="Pattern to filter test files (e.g., 'test_message*.py')")
    parser.add_argument("-x", "--stop-on-failure", action="store_true", help="Stop test execution on first failure")
    parser.add_argument("--skip-header", action="store_true", help="Skip printing the header")
    args = parser.parse_args()
    
    if not args.skip_header:
        print_header()
    
    if args.setup:
        setup_env()
    
    sys.exit(run_tests(
        coverage=args.coverage, 
        verbose=args.verbose, 
        pattern=args.pattern,
        stop_on_failure=args.stop_on_failure
    ))

if __name__ == "__main__":
    main()
