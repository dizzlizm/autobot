#!/usr/bin/env python3
"""
Quick self-improvement for Autobot.

A simplified flow that:
1. Reads autobot's source files
2. Asks the local model for improvement suggestions
3. Generates tasks from suggestions
4. Executes the tasks

Usage:
    python3 self_improve.py
    python3 self_improve.py --model ollama/qwen2.5-coder:7b
    python3 self_improve.py --dry-run
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_MODEL = "qwen2.5-coder:3b"


def log(msg):
    """Simple logging."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def ask_model(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Ask the local Ollama model a question."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout.strip()
    except Exception as e:
        log(f"Model call failed: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Quick self-improvement for Autobot",
        epilog="Note: Use 'python3 autobot.py improve' for the full self-improvement cycle."
    )
    parser.add_argument("--model", "-m", default=f"ollama/{DEFAULT_MODEL}",
                        help=f"Model to use (default: ollama/{DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show the plan without executing")
    args = parser.parse_args()

    model_name = args.model.replace("ollama/", "")

    log("=" * 50)
    log("AUTOBOT QUICK IMPROVEMENT")
    log(f"Model: {model_name}")
    log("=" * 50)

    # Step 1: Read source files
    log("\nStep 1: Reading source files...")

    source_files = list(SCRIPT_DIR.glob("*.py"))
    source_content = ""

    for f in sorted(source_files)[:4]:  # Top 4 files
        content = f.read_text()[:2500]  # First 2500 chars
        source_content += f"\n\n=== {f.name} ===\n{content}"

    log(f"Read {len(source_files)} Python files")

    # Step 2: Ask model for improvements
    log("\nStep 2: Asking model for improvement suggestions...")

    analysis_prompt = f"""You are analyzing Autobot, a self-improving AI agent written in Python.

Review this code and suggest 3 small, focused improvements.

{source_content}

For each improvement:
1. Which file to change
2. What specific change to make
3. Why it improves the code

Keep suggestions SMALL and SIMPLE. Prefer:
- Bug fixes
- Error handling improvements
- Code clarity improvements
- Performance optimizations

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

    # Step 3: Convert to tasks
    log("\nStep 3: Generating task file...")

    tasks_prompt = f"""Convert these improvement suggestions into task format for Aider.

SUGGESTIONS:
{suggestions}

Write in this exact markdown format:

## Task 1: [title]
[Detailed description of what to change, including the file name and specific code changes]

## Task 2: [title]
[Detailed description]

## Task 3: [title]
[Detailed description]

Be very specific about file names and what code to write."""

    tasks_md = ask_model(tasks_prompt, model_name)

    if not tasks_md or "## Task" not in tasks_md:
        log("Failed to generate valid tasks")
        if tasks_md:
            print(tasks_md)
        return 1

    # Save tasks
    tasks_file = SCRIPT_DIR / "quick_tasks.md"
    tasks_file.write_text(
        f"# Quick Self-Improvement Tasks\n"
        f"Generated: {datetime.now().isoformat()}\n"
        f"Model: {model_name}\n\n"
        f"{tasks_md}"
    )

    print("\n" + "=" * 50)
    print("GENERATED TASKS:")
    print("=" * 50)
    print(tasks_md)
    print("=" * 50)

    log(f"\nTasks saved to: {tasks_file}")

    if args.dry_run:
        log("\n[DRY RUN] Would now execute these tasks")
        return 0

    # Step 4: Execute tasks
    log("\nStep 4: Executing improvements...")

    from runner import TaskRunner

    runner = TaskRunner(
        project_path=str(SCRIPT_DIR),
        model=args.model,
        dry_run=False,
        verbose=True
    )

    branch = f"autobot-quick-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    result = runner.run_tasks_from_file(tasks_file, branch)

    log("\n" + "=" * 50)
    if result == 0:
        log("QUICK IMPROVEMENT COMPLETE!")
        log(f"Check branch: {branch}")
        log("Run 'git log --oneline' to see changes")
    else:
        log("QUICK IMPROVEMENT HAD ISSUES")
        log("Check the branch for partial progress")
    log("=" * 50)

    return result


if __name__ == "__main__":
    sys.exit(main())
