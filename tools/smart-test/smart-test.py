#!/usr/bin/env python3
"""
Smart Test Runner
Auto-detects project type and runs appropriate tests/linting.
Designed to be called by Aider or overnight.py.

Usage:
    smart-test.py detect /path/to/project    # Detect project type
    smart-test.py test /path/to/project      # Run tests
    smart-test.py lint /path/to/project      # Run linting
    smart-test.py all /path/to/project       # Run both test and lint
    smart-test.py browser /path/to/file.html # Browser test for HTML
"""

import sys
import os
import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
TOOLS_DIR = SCRIPT_DIR.parent


def detect_project(project_path: Path) -> dict:
    """Detect project type and available tooling."""
    types = []

    files = list(project_path.iterdir()) if project_path.is_dir() else []
    file_names = [f.name for f in files]

    # Check package.json for Node.js projects
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        types.append("nodejs")
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "react" in deps: types.append("react")
            if "vue" in deps: types.append("vue")
            if "express" in deps: types.append("express")
            if "typescript" in deps: types.append("typescript")
            if "jest" in deps: types.append("jest")
            if "mocha" in deps: types.append("mocha")
            if "vitest" in deps: types.append("vitest")
            if "eslint" in deps: types.append("eslint")
        except:
            pass

    # Python
    if any(f in file_names for f in ["requirements.txt", "pyproject.toml", "setup.py"]):
        types.append("python")

    # Other languages
    if "Cargo.toml" in file_names: types.append("rust")
    if "go.mod" in file_names: types.append("go")
    if "pom.xml" in file_names or "build.gradle" in file_names: types.append("java")

    # Web files (vanilla JS/HTML)
    if any(f.endswith(".html") for f in file_names):
        types.append("html")
    if any(f.endswith(".js") for f in file_names) and "package.json" not in file_names:
        types.append("vanilla-js")

    return {
        "types": types if types else ["unknown"],
        "has_package_json": pkg_json.exists(),
        "has_node_modules": (project_path / "node_modules").exists(),
    }


def get_test_command(project_path: Path, info: dict) -> str | None:
    """Get the appropriate test command for the project."""
    types = info["types"]

    if any(t in types for t in ["jest", "vitest", "mocha"]):
        return "npm test"

    if "nodejs" in types:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            test_script = pkg.get("scripts", {}).get("test", "")
            if test_script and "no test specified" not in test_script:
                return "npm test"

    if "python" in types: return "pytest"
    if "rust" in types: return "cargo test"
    if "go" in types: return "go test ./..."

    # For HTML/vanilla-js, use browser test
    if "html" in types or "vanilla-js" in types:
        return "browser"  # Special marker

    return None


def get_lint_command(project_path: Path, info: dict) -> str | None:
    """Get the appropriate lint command for the project."""
    types = info["types"]

    if "typescript" in types:
        return "npx tsc --noEmit"

    if "eslint" in types:
        return "npm run lint"

    if "nodejs" in types:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            if "lint" in pkg.get("scripts", {}):
                return "npm run lint"
        return "npx eslint ."

    if "vanilla-js" in types or "html" in types:
        # Use our custom linter
        return f"{TOOLS_DIR}/lint/lint"

    if "python" in types: return "ruff check . || python -m flake8"
    if "rust" in types: return "cargo clippy"
    if "go" in types: return "go vet ./..."

    return None


def run_command(cmd: str, cwd: Path, timeout: int = 120) -> tuple[bool, str]:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def run_browser_test(html_path: Path) -> tuple[bool, str]:
    """Run browser test using our Puppeteer tool."""
    browser_test = TOOLS_DIR / "browser-test" / "test"
    if not browser_test.exists():
        return False, f"Browser test tool not found at {browser_test}"

    success, output = run_command(f'"{browser_test}" "{html_path}"', html_path.parent)
    return success, output


def cmd_detect(project_path: Path):
    """Handle detect command."""
    info = detect_project(project_path)
    test_cmd = get_test_command(project_path, info)
    lint_cmd = get_lint_command(project_path, info)

    result = {
        **info,
        "test_command": test_cmd,
        "lint_command": lint_cmd,
    }
    print(json.dumps(result, indent=2))
    return True


def cmd_test(project_path: Path) -> bool:
    """Handle test command."""
    info = detect_project(project_path)
    test_cmd = get_test_command(project_path, info)

    if not test_cmd:
        print("No test command detected for this project type.")
        print(f"Detected types: {info['types']}")
        return False

    print(f"Project types: {info['types']}")
    print(f"Running: {test_cmd}")
    print("-" * 40)

    if test_cmd == "browser":
        # Find HTML files
        html_files = list(project_path.glob("*.html"))
        if not html_files:
            html_files = list(project_path.glob("**/*.html"))

        if not html_files:
            print("No HTML files found for browser testing.")
            return False

        # Test index.html first if it exists, otherwise first found
        index = project_path / "index.html"
        test_file = index if index.exists() else html_files[0]

        success, output = run_browser_test(test_file)
        print(output)
        return success

    success, output = run_command(test_cmd, project_path)
    print(output)

    if success:
        print("\n✓ TESTS PASSED")
    else:
        print("\n✗ TESTS FAILED")

    return success


def cmd_lint(project_path: Path) -> bool:
    """Handle lint command."""
    info = detect_project(project_path)
    lint_cmd = get_lint_command(project_path, info)

    if not lint_cmd:
        print("No lint command detected for this project type.")
        print(f"Detected types: {info['types']}")
        return False

    print(f"Project types: {info['types']}")
    print(f"Running: {lint_cmd}")
    print("-" * 40)

    # For vanilla JS, lint all JS files
    if "vanilla-js" in info["types"] or "html" in info["types"]:
        js_files = list(project_path.glob("*.js"))
        if not js_files:
            print("No JS files found to lint.")
            return True  # Not a failure, just nothing to do

        all_passed = True
        for js_file in js_files:
            success, output = run_command(f'{lint_cmd} "{js_file}"', project_path)
            print(f"\n{js_file.name}:")
            print(output)
            if not success:
                all_passed = False

        return all_passed

    success, output = run_command(lint_cmd, project_path)
    print(output)

    if success:
        print("\n✓ LINT PASSED")
    else:
        print("\n✗ LINT FAILED")

    return success


def cmd_browser(html_path: Path) -> bool:
    """Handle browser test command."""
    if not html_path.exists():
        print(f"File not found: {html_path}")
        return False

    print(f"Browser testing: {html_path}")
    print("-" * 40)

    success, output = run_browser_test(html_path)
    print(output)
    return success


def cmd_all(project_path: Path) -> bool:
    """Run both tests and linting."""
    print("=" * 40)
    print("RUNNING TESTS")
    print("=" * 40)
    test_ok = cmd_test(project_path)

    print("\n" + "=" * 40)
    print("RUNNING LINT")
    print("=" * 40)
    lint_ok = cmd_lint(project_path)

    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print(f"Tests: {'✓ PASSED' if test_ok else '✗ FAILED'}")
    print(f"Lint:  {'✓ PASSED' if lint_ok else '✗ FAILED'}")

    return test_ok and lint_ok


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    target = Path(sys.argv[2]).resolve()

    commands = {
        "detect": cmd_detect,
        "test": cmd_test,
        "lint": cmd_lint,
        "browser": cmd_browser,
        "all": cmd_all,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    success = commands[command](target)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
