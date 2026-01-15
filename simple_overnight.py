#!/usr/bin/env python3
"""
Simple overnight task runner - no fancy features, just works.

Usage:
    python3 simple_overnight.py --project ./my-app --tasks tasks.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def parse_tasks(tasks_file):
    """Parse ## headers from markdown file."""
    with open(tasks_file) as f:
        content = f.read()

    tasks = []
    pattern = r"##\s+(?:Task\s+\d+:\s*)?(.+?)(?=\n##|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)

    for i, match in enumerate(matches, 1):
        lines = match.strip().split("\n", 1)
        title = lines[0].strip()
        desc = lines[1].strip() if len(lines) > 1 else title

        if title.lower() in ["summary", "notes", "config"]:
            continue

        tasks.append({"id": i, "title": title, "description": desc})

    return tasks

def run_aider(project_path, task, model):
    """Run aider for one task."""
    prompt = f"""## Task: {task['title']}

{task['description']}

Keep changes minimal. Follow existing code style."""

    cmd = [
        "aider",
        "--model", model,
        "--yes",
        "--auto-commits",
        "--no-stream",
        "--message", prompt,
    ]

    log(f"Running: {task['title'][:50]}...")

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=1800
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Simple overnight task runner")
    parser.add_argument("--project", "-p", required=True, help="Project directory")
    parser.add_argument("--tasks", "-t", required=True, help="Tasks markdown file")
    parser.add_argument("--model", "-m", default="ollama/qwen2.5-coder:3b", help="Model to use")
    parser.add_argument("--dry-run", action="store_true", help="Just show tasks")

    args = parser.parse_args()

    project = Path(args.project).resolve()
    tasks_file = Path(args.tasks).resolve()

    # Create project if needed
    if not project.exists():
        log(f"Creating {project}")
        project.mkdir(parents=True)
        os.chdir(project)
        subprocess.run(["git", "init"], capture_output=True)

    # Parse tasks
    tasks = parse_tasks(tasks_file)
    log(f"Found {len(tasks)} tasks")

    if args.dry_run:
        for t in tasks:
            print(f"  {t['id']}. {t['title']}")
        return 0

    # Run each task
    os.chdir(project)
    completed = 0

    for task in tasks:
        log(f"\n{'='*50}")
        log(f"TASK {task['id']}/{len(tasks)}: {task['title']}")
        log(f"{'='*50}")

        success, output = run_aider(project, task, args.model)

        if success:
            log(f"✓ Task {task['id']} completed")
            completed += 1
        else:
            log(f"✗ Task {task['id']} failed")
            print(output[-500:] if len(output) > 500 else output)

    log(f"\nDone: {completed}/{len(tasks)} tasks completed")
    return 0 if completed == len(tasks) else 1

if __name__ == "__main__":
    sys.exit(main())
