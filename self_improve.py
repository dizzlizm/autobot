#!/usr/bin/env python3
"""
Let the small model try to improve itself.
Just run it and see what happens.

Usage:
    python3 self_improve.py
    python3 self_improve.py --model ollama/qwen2.5-coder:7b
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ask_model(prompt, model="qwen2.5-coder:3b"):
    """Ask the model a question."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout.strip()
    except:
        return ""

def main():
    parser = argparse.ArgumentParser(description="Let the model improve itself")
    parser.add_argument("--model", "-m", default="ollama/qwen2.5-coder:3b")
    parser.add_argument("--dry-run", action="store_true", help="Just show the plan")
    args = parser.parse_args()

    model_name = args.model.replace("ollama/", "")

    log("=" * 50)
    log("SELF-IMPROVEMENT EXPERIMENT")
    log(f"Model: {model_name}")
    log("=" * 50)

    # Read our own source files
    log("\nStep 1: Reading source files...")

    source_files = list(SCRIPT_DIR.glob("*.py"))
    source_content = ""

    for f in source_files[:3]:  # Limit to 3 files
        content = f.read_text()[:2000]  # First 2000 chars
        source_content += f"\n\n=== {f.name} ===\n{content}"

    log(f"Read {len(source_files)} files")

    # Ask model what to improve
    log("\nStep 2: Asking model what to improve...")

    analysis_prompt = f"""You are analyzing a Python project. Look at this code and suggest 3 small improvements.

{source_content}

List exactly 3 improvements. For each one:
- Which file to change
- What to change (be specific)
- Why it helps

Keep suggestions SMALL and SIMPLE. One-line fixes are best.
Format as a numbered list."""

    suggestions = ask_model(analysis_prompt, model_name)

    if not suggestions:
        log("Model didn't respond")
        return 1

    print("\n" + "=" * 50)
    print("MODEL SUGGESTIONS:")
    print("=" * 50)
    print(suggestions)
    print("=" * 50)

    # Generate tasks file
    log("\nStep 3: Generating tasks...")

    tasks_prompt = f"""Convert these suggestions into task format.

SUGGESTIONS:
{suggestions}

Write in this exact format (markdown with ## headers):

## Task 1: [title]
[detailed description of what to change]

## Task 2: [title]
[detailed description of what to change]

## Task 3: [title]
[detailed description of what to change]

Be very specific about file names and what code to write."""

    tasks_md = ask_model(tasks_prompt, model_name)

    if not tasks_md or "## Task" not in tasks_md:
        log("Failed to generate tasks")
        print(tasks_md)
        return 1

    # Save tasks
    tasks_file = SCRIPT_DIR / "self_tasks.md"
    tasks_file.write_text(f"# Self-Improvement Tasks\nGenerated: {datetime.now()}\n\n{tasks_md}")

    print("\n" + "=" * 50)
    print("GENERATED TASKS:")
    print("=" * 50)
    print(tasks_md)
    print("=" * 50)

    log(f"\nTasks saved to: {tasks_file}")

    if args.dry_run:
        log("\n[DRY RUN] Would now run these tasks")
        return 0

    # Run the tasks
    log("\nStep 4: Executing self-improvement...")

    # Create a branch for safety
    subprocess.run(
        ["git", "checkout", "-b", f"self-improve-{datetime.now().strftime('%Y%m%d-%H%M%S')}"],
        cwd=SCRIPT_DIR,
        capture_output=True
    )

    cmd = [
        "python3", str(SCRIPT_DIR / "simple_overnight.py"),
        "--project", str(SCRIPT_DIR),
        "--tasks", str(tasks_file),
        "--model", args.model
    ]

    log(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    log("\n" + "=" * 50)
    if result.returncode == 0:
        log("SELF-IMPROVEMENT COMPLETE!")
        log("Check git log to see what changed")
    else:
        log("SELF-IMPROVEMENT HAD ISSUES")
        log("Check the branch to see partial progress")
    log("=" * 50)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
