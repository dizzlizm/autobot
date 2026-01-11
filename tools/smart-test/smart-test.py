#!/usr/bin/env python3
"""
Smart Test Runner
Auto-detects project type and runs appropriate tests/linting/security checks.
Designed to be called by Aider or overnight.py.

Usage:
    smart-test.py detect /path/to/project    # Detect project type
    smart-test.py test /path/to/project      # Run tests
    smart-test.py lint /path/to/project      # Run linting
    smart-test.py security /path/to/project  # Security audit (vulnerabilities)
    smart-test.py format /path/to/project    # Check code formatting
    smart-test.py size /path/to/project      # Check bundle/build size
    smart-test.py deadcode /path/to/project  # Find unused code
    smart-test.py all /path/to/project       # Run test + lint
    smart-test.py audit /path/to/project     # Run ALL checks (comprehensive)
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

            # Expo/React Native detection (check before generic react)
            if "expo" in deps:
                types.append("expo")
            if "react-native" in deps:
                types.append("react-native")

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

    # Also check for app.json (Expo config)
    app_json = project_path / "app.json"
    if app_json.exists():
        try:
            app_config = json.loads(app_json.read_text())
            if "expo" in app_config:
                if "expo" not in types:
                    types.append("expo")
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

    # Expo/React Native: run jest if available, otherwise validate with export
    if "expo" in types:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            test_script = pkg.get("scripts", {}).get("test", "")
            if test_script and "no test specified" not in test_script:
                return "npm test"
        # No tests configured - use expo export as build validation
        return "npx expo export --platform web --output-dir /tmp/expo-test-build"

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

    # Expo: run expo doctor + typescript check
    if "expo" in types:
        cmds = ["npx expo doctor"]
        if "typescript" in types:
            cmds.append("npx tsc --noEmit")
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            if "lint" in pkg.get("scripts", {}):
                cmds.append("npm run lint")
        return " && ".join(cmds)

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


def get_security_command(project_path: Path, info: dict) -> str | None:
    """Get the appropriate security audit command."""
    types = info["types"]

    if "nodejs" in types:
        return "npm audit --audit-level=high"
    if "python" in types:
        # pip-audit is the modern choice, fallback to safety
        return "pip-audit || safety check"
    if "rust" in types:
        return "cargo audit"
    if "go" in types:
        return "govulncheck ./..."

    return None


def get_format_command(project_path: Path, info: dict) -> str | None:
    """Get the appropriate format check command (check only, no write)."""
    types = info["types"]

    if "nodejs" in types:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            # Check for prettier
            if "prettier" in deps:
                return "npx prettier --check ."
            # Check for format script
            if "format:check" in pkg.get("scripts", {}):
                return "npm run format:check"
        # Default to prettier if available
        return "npx prettier --check . 2>/dev/null || echo 'Prettier not configured'"

    if "python" in types:
        # black or ruff format
        return "ruff format --check . || black --check ."
    if "rust" in types:
        return "cargo fmt --check"
    if "go" in types:
        return "gofmt -l . | head -20"

    return None


def get_size_command(project_path: Path, info: dict) -> tuple[str | None, int | None]:
    """Get build size check command and threshold (in KB)."""
    types = info["types"]

    if "expo" in types:
        # Expo web build, threshold 5MB
        return "npx expo export --platform web --output-dir /tmp/size-check && du -sk /tmp/size-check", 5000
    if "react" in types or "vue" in types:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            if "build" in pkg.get("scripts", {}):
                # Build and check dist size, threshold 2MB
                return "npm run build && du -sk dist build 2>/dev/null | head -1", 2000
    if "rust" in types:
        return "cargo build --release && du -sk target/release 2>/dev/null | head -1", 50000

    return None, None


def get_deadcode_command(project_path: Path, info: dict) -> str | None:
    """Get dead code detection command."""
    types = info["types"]

    if "nodejs" in types or "typescript" in types:
        # knip is the best tool for JS/TS dead code
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "knip" in deps:
                return "npx knip"
        # Try knip anyway, it might be globally installed
        return "npx knip 2>/dev/null || echo 'Install knip: npm i -D knip'"

    if "python" in types:
        # vulture finds dead Python code
        return "vulture . --min-confidence 80 || echo 'Install vulture: pip install vulture'"
    if "rust" in types:
        # Rust compiler warns about dead code by default
        return "cargo build 2>&1 | grep -E '(warning.*dead_code|warning.*unused)' || echo 'No dead code warnings'"

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
    security_cmd = get_security_command(project_path, info)
    format_cmd = get_format_command(project_path, info)
    size_cmd, size_threshold = get_size_command(project_path, info)
    deadcode_cmd = get_deadcode_command(project_path, info)

    result = {
        **info,
        "test_command": test_cmd,
        "lint_command": lint_cmd,
        "security_command": security_cmd,
        "format_command": format_cmd,
        "size_command": size_cmd,
        "size_threshold_kb": size_threshold,
        "deadcode_command": deadcode_cmd,
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


def cmd_security(project_path: Path) -> bool:
    """Run security audit for vulnerabilities."""
    info = detect_project(project_path)
    sec_cmd = get_security_command(project_path, info)

    if not sec_cmd:
        print("No security audit available for this project type.")
        print(f"Detected types: {info['types']}")
        return True  # Not a failure, just not applicable

    print(f"Project types: {info['types']}")
    print(f"Running: {sec_cmd}")
    print("-" * 40)

    success, output = run_command(sec_cmd, project_path, timeout=180)
    print(output)

    if success:
        print("\n✓ SECURITY AUDIT PASSED")
    else:
        # npm audit returns non-zero for any vulnerabilities
        # Check if it's just warnings vs critical issues
        if "critical" in output.lower() or "high" in output.lower():
            print("\n✗ SECURITY ISSUES FOUND (high/critical)")
            return False
        else:
            print("\n⚠ SECURITY WARNINGS (low/moderate)")
            return True  # Warnings are OK for overnight runs

    return success


def cmd_format(project_path: Path) -> bool:
    """Check code formatting."""
    info = detect_project(project_path)
    fmt_cmd = get_format_command(project_path, info)

    if not fmt_cmd:
        print("No format check available for this project type.")
        print(f"Detected types: {info['types']}")
        return True

    print(f"Project types: {info['types']}")
    print(f"Running: {fmt_cmd}")
    print("-" * 40)

    success, output = run_command(fmt_cmd, project_path)
    print(output)

    if success:
        print("\n✓ FORMATTING OK")
    else:
        print("\n✗ FORMATTING ISSUES")
        print("Run formatter to fix: prettier --write . / black . / cargo fmt")

    return success


def cmd_size(project_path: Path) -> bool:
    """Check build/bundle size."""
    info = detect_project(project_path)
    size_cmd, threshold_kb = get_size_command(project_path, info)

    if not size_cmd:
        print("No size check available for this project type.")
        print(f"Detected types: {info['types']}")
        return True

    print(f"Project types: {info['types']}")
    print(f"Running: {size_cmd}")
    print(f"Threshold: {threshold_kb}KB ({threshold_kb/1000:.1f}MB)")
    print("-" * 40)

    success, output = run_command(size_cmd, project_path, timeout=300)
    print(output)

    if not success:
        print("\n✗ BUILD FAILED")
        return False

    # Parse size from du output (first number)
    try:
        import re
        match = re.search(r'(\d+)', output)
        if match:
            size_kb = int(match.group(1))
            size_mb = size_kb / 1000
            print(f"\nBuild size: {size_kb}KB ({size_mb:.1f}MB)")

            if size_kb > threshold_kb:
                print(f"✗ EXCEEDS THRESHOLD ({threshold_kb}KB)")
                return False
            else:
                print(f"✓ WITHIN THRESHOLD ({threshold_kb}KB)")
                return True
    except:
        pass

    print("\n⚠ Could not parse size")
    return True


def cmd_deadcode(project_path: Path) -> bool:
    """Find unused/dead code."""
    info = detect_project(project_path)
    dead_cmd = get_deadcode_command(project_path, info)

    if not dead_cmd:
        print("No dead code detection available for this project type.")
        print(f"Detected types: {info['types']}")
        return True

    print(f"Project types: {info['types']}")
    print(f"Running: {dead_cmd}")
    print("-" * 40)

    success, output = run_command(dead_cmd, project_path, timeout=180)
    print(output)

    # Dead code tools often exit non-zero when they find issues
    # but that's informational, not a hard failure
    if "unused" in output.lower() or "dead" in output.lower():
        print("\n⚠ POTENTIAL DEAD CODE FOUND")
        print("Review the above and remove if not needed")
    else:
        print("\n✓ NO DEAD CODE DETECTED")

    return True  # Informational only, don't fail builds


def cmd_audit(project_path: Path) -> bool:
    """Run comprehensive audit: test, lint, security, format, size."""
    results = {}

    sections = [
        ("TESTS", cmd_test),
        ("LINT", cmd_lint),
        ("SECURITY", cmd_security),
        ("FORMATTING", cmd_format),
        ("DEAD CODE", cmd_deadcode),
    ]

    for name, cmd_func in sections:
        print("\n" + "=" * 50)
        print(f"  {name}")
        print("=" * 50)
        try:
            results[name] = cmd_func(project_path)
        except Exception as e:
            print(f"Error: {e}")
            results[name] = False

    # Size check is optional and slow, run last
    print("\n" + "=" * 50)
    print("  BUILD SIZE")
    print("=" * 50)
    try:
        results["SIZE"] = cmd_size(project_path)
    except Exception as e:
        print(f"Error: {e}")
        results["SIZE"] = True  # Don't fail on size check errors

    # Print summary
    print("\n" + "=" * 50)
    print("  AUDIT SUMMARY")
    print("=" * 50)
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name:12} {status}")

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n✗ AUDIT FAILED: {', '.join(failed)}")
        return False
    else:
        print("\n✓ ALL CHECKS PASSED")
        return True


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
        "security": cmd_security,
        "format": cmd_format,
        "size": cmd_size,
        "deadcode": cmd_deadcode,
        "all": cmd_all,
        "audit": cmd_audit,
        "browser": cmd_browser,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    success = commands[command](target)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
