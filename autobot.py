#!/usr/bin/env python3
"""
Autobot - Self-Improving AI Agent

Autobot is an AI system that analyzes and improves its own source code.
It uses local LLMs (via Ollama) to examine its codebase, identify improvements,
generate tasks, execute changes, and learn from outcomes.

This is the main entry point for all autobot operations.

Usage:
    # Analyze autobot's own code for improvements
    python3 autobot.py analyze

    # Run self-improvement cycle (analyze -> generate tasks -> execute)
    python3 autobot.py improve

    # Quick self-improvement with minimal output
    python3 autobot.py quick

    # Show learning history and insights
    python3 autobot.py history

    # Run a specific improvement task
    python3 autobot.py run-task "Fix error handling in analyzer"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Autobot's own directory
AUTOBOT_DIR = Path(__file__).parent.resolve()

def log(msg: str, level: str = "INFO"):
    """Simple logging."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "", "WARN": "[!]", "ERROR": "[X]", "OK": "[+]"}.get(level, "")
    print(f"[{timestamp}] {prefix} {msg}")


def cmd_analyze(args):
    """Analyze autobot's own codebase for improvement opportunities."""
    from self_modify import SelfAnalyzer

    log("=" * 50)
    log("AUTOBOT SELF-ANALYSIS")
    log("=" * 50)

    analyzer = SelfAnalyzer(verbose=not args.quiet)
    results = analyzer.analyze_codebase()

    issues = results.get("issues", [])
    files_analyzed = results.get("files_analyzed", 0)

    print()
    log(f"Files analyzed: {files_analyzed}")
    log(f"Issues found: {len(issues)}")

    if issues and not args.quiet:
        print()
        log("Top Issues:")
        for i, issue in enumerate(issues[:10], 1):
            severity = issue.get("severity", "?").upper()
            desc = issue.get("description", "Unknown")[:70]
            file = issue.get("file", "unknown")
            print(f"  {i}. [{severity}] {desc}")
            print(f"     -> {file}")

    # Optionally generate improvement plan
    if args.plan:
        print()
        log("Generating improvement plan...")
        plan = analyzer.generate_improvement_plan()
        print()
        print(plan)

    return 0


def cmd_improve(args):
    """Run full self-improvement cycle."""
    from self_modify import SelfModifyRunner

    log("=" * 50)
    log("AUTOBOT SELF-IMPROVEMENT")
    log("=" * 50)

    runner = SelfModifyRunner(
        verbose=not args.quiet,
        dry_run=args.dry_run,
        hybrid=False,  # Pure local model for self-contained operation
        prompt_loop=args.prompt_loop
    )

    return runner.run_improvement(max_tasks=args.max_tasks)


def cmd_quick(args):
    """Quick self-improvement with simplified flow."""
    from self_improve import main as quick_improve

    log("=" * 50)
    log("AUTOBOT QUICK IMPROVEMENT")
    log("=" * 50)

    # Simulate args for self_improve
    sys.argv = ["self_improve.py"]
    if args.dry_run:
        sys.argv.append("--dry-run")
    if args.model:
        sys.argv.extend(["--model", args.model])

    return quick_improve()


def cmd_history(args):
    """Show learning history and insights."""
    from self_modify import LearningEngine

    log("=" * 50)
    log("AUTOBOT LEARNING HISTORY")
    log("=" * 50)

    engine = LearningEngine()
    engine.print_history()

    suggestions = engine.suggest_adjustments()
    if suggestions:
        print()
        log("Suggested Adjustments:")
        for s in suggestions:
            print(f"  - {s}")

    return 0


def cmd_run_task(args):
    """Run a specific improvement task."""
    from runner import TaskRunner

    task_description = args.task
    if not task_description:
        log("No task specified", "ERROR")
        return 1

    log("=" * 50)
    log("AUTOBOT TASK EXECUTION")
    log("=" * 50)
    log(f"Task: {task_description[:60]}...")

    runner = TaskRunner(
        project_path=str(AUTOBOT_DIR),
        dry_run=args.dry_run,
        model=args.model
    )

    return runner.run_single_task(task_description)


def cmd_status(args):
    """Show autobot status and configuration."""
    import subprocess

    log("=" * 50)
    log("AUTOBOT STATUS")
    log("=" * 50)

    # Check Python files
    py_files = list(AUTOBOT_DIR.glob("*.py"))
    log(f"Source files: {len(py_files)}")
    for f in py_files:
        lines = len(f.read_text().split("\n"))
        log(f"  {f.name}: {lines} lines")

    # Check Ollama
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            models = [l.split()[0] for l in result.stdout.strip().split("\n")[1:] if l.strip()]
            log(f"Ollama models available: {len(models)}")
            for m in models[:5]:
                log(f"  - {m}")
        else:
            log("Ollama not responding", "WARN")
    except Exception as e:
        log(f"Ollama check failed: {e}", "WARN")

    # Check git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=AUTOBOT_DIR
        )
        changes = len([l for l in result.stdout.split("\n") if l.strip()])
        log(f"Uncommitted changes: {changes}")
    except Exception:
        pass

    # Check learning history
    history_file = AUTOBOT_DIR / "self_modify_history.json"
    if history_file.exists():
        import json
        with open(history_file) as f:
            data = json.load(f)
        records = len(data.get("records", []))
        log(f"Learning records: {records}")
    else:
        log("Learning history: None yet")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="autobot",
        description="Autobot - Self-Improving AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze autobot for improvements
    python3 autobot.py analyze
    python3 autobot.py analyze --plan

    # Run self-improvement
    python3 autobot.py improve
    python3 autobot.py improve --dry-run
    python3 autobot.py improve --max-tasks 3

    # Quick improvement (simplified)
    python3 autobot.py quick

    # View learning history
    python3 autobot.py history

    # Check status
    python3 autobot.py status

    # Run specific task
    python3 autobot.py run-task "Add better error handling to analyzer"
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    p_analyze = subparsers.add_parser("analyze", help="Analyze codebase for improvements")
    p_analyze.add_argument("--plan", action="store_true", help="Generate improvement plan")
    p_analyze.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    p_analyze.set_defaults(func=cmd_analyze)

    # Improve command
    p_improve = subparsers.add_parser("improve", help="Run self-improvement cycle")
    p_improve.add_argument("--dry-run", action="store_true", help="Preview without changes")
    p_improve.add_argument("--max-tasks", type=int, default=5, help="Max tasks to run")
    p_improve.add_argument("--prompt-loop", action="store_true", help="Use iterative prompt refinement")
    p_improve.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    p_improve.set_defaults(func=cmd_improve)

    # Quick command
    p_quick = subparsers.add_parser("quick", help="Quick self-improvement")
    p_quick.add_argument("--dry-run", action="store_true", help="Preview without changes")
    p_quick.add_argument("--model", "-m", help="Model to use")
    p_quick.set_defaults(func=cmd_quick)

    # History command
    p_history = subparsers.add_parser("history", help="Show learning history")
    p_history.set_defaults(func=cmd_history)

    # Status command
    p_status = subparsers.add_parser("status", help="Show autobot status")
    p_status.set_defaults(func=cmd_status)

    # Run-task command
    p_task = subparsers.add_parser("run-task", help="Run a specific task")
    p_task.add_argument("task", help="Task description")
    p_task.add_argument("--dry-run", action="store_true", help="Preview without changes")
    p_task.add_argument("--model", "-m", default="ollama/qwen2.5-coder:3b", help="Model to use")
    p_task.set_defaults(func=cmd_run_task)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
