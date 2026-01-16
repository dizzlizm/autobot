#!/usr/bin/env python3
"""
Task Runner for Autobot Self-Improvement

A simplified task execution engine that runs improvement tasks on autobot's own codebase.
Uses Aider with local Ollama models for code generation.

This module is used internally by autobot.py and self_modify.py.
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
AUTOBOT_DIR = Path(__file__).parent.resolve()
DEFAULT_MODEL = "ollama/qwen2.5-coder:3b"  # Good balance of quality and speed
TASK_TIMEOUT = 1200  # 20 minutes per task
STATE_FILE = "runner_state.json"
LOG_DIR = AUTOBOT_DIR / "logs"
REPORT_DIR = AUTOBOT_DIR / "reports"

# Aider command - check if wrapper exists, otherwise use direct
AIDER_CMD = AUTOBOT_DIR / "aider"
if not AIDER_CMD.exists():
    AIDER_CMD = "aider"  # Fall back to system aider


@dataclass
class Task:
    """Represents a single improvement task."""
    id: int
    title: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: int = 0
    commits: list = field(default_factory=list)
    error: Optional[str] = None
    output: str = ""


@dataclass
class RunnerState:
    """Tracks runner state for recovery."""
    branch: str
    start_time: str
    tasks: list = field(default_factory=list)
    current_task_index: int = 0
    completed_count: int = 0
    failed_count: int = 0


class TaskRunner:
    """Executes improvement tasks on autobot's codebase."""

    def __init__(
        self,
        project_path: str = None,
        model: str = DEFAULT_MODEL,
        timeout: int = TASK_TIMEOUT,
        dry_run: bool = False,
        verbose: bool = True,
    ):
        self.project_path = Path(project_path or AUTOBOT_DIR).resolve()
        self.model = model
        self.timeout = timeout
        self.dry_run = dry_run
        self.verbose = verbose
        self.state: Optional[RunnerState] = None

        # Ensure directories exist
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"INFO": "", "WARN": "[!]", "ERROR": "[X]", "OK": "[+]"}.get(level, "")
            print(f"[{timestamp}] {prefix} {message}")

    def get_current_commit(self) -> str:
        """Get current git commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=self.project_path
        )
        return result.stdout.strip()

    def get_commits_since(self, since_hash: str) -> list[str]:
        """Get commits made since a given hash."""
        result = subprocess.run(
            ["git", "log", "--oneline", f"{since_hash}..HEAD"],
            capture_output=True,
            text=True,
            cwd=self.project_path
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
        return []

    def setup_branch(self, branch_name: str):
        """Create or checkout a branch for self-improvement work."""
        os.chdir(self.project_path)

        # Check current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True
        )
        current = result.stdout.strip()

        if current == branch_name:
            self.log(f"Already on branch: {branch_name}")
            return

        # Check if branch exists
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True
        )

        if result.returncode == 0:
            subprocess.run(["git", "checkout", branch_name], check=True)
            self.log(f"Checked out: {branch_name}")
        else:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            self.log(f"Created branch: {branch_name}")

    def build_prompt(self, task: Task) -> str:
        """Build a focused prompt for the task."""
        return f"""## Self-Improvement Task

{task.title}

## Details

{task.description}

## Context

You are improving Autobot's own source code. Autobot is a self-improving AI agent
written in Python that uses Ollama for local LLM inference.

Key files:
- autobot.py: Main entry point and CLI
- self_modify.py: Self-analysis and task generation
- runner.py: Task execution engine
- self_improve.py: Quick improvement flow

## Requirements

1. Make minimal, focused changes
2. Follow existing code patterns
3. Keep the same formatting style
4. Do NOT add unnecessary comments
5. Test that changes don't break functionality

Now implement the improvement."""

    def run_aider(self, message: str) -> tuple[bool, str, list[str]]:
        """Run Aider with a message and return (success, output, commits)."""
        commit_before = self.get_current_commit()

        cmd = [
            str(AIDER_CMD),
            "--model", self.model,
            "--yes",
            "--auto-commits",
            "--no-stream",
            "--message", message,
        ]

        self.log(f"Running Aider with {self.model}...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.project_path
            )

            output_lines = []
            start = time.time()

            while True:
                if time.time() - start > self.timeout:
                    process.kill()
                    return False, "Timeout exceeded", []

                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    if self.verbose:
                        print(f"  {line.rstrip()}")
                    output_lines.append(line)

            output = "".join(output_lines)
            success = process.returncode == 0

            # Get new commits
            commits = self.get_commits_since(commit_before)

            return success, output, commits

        except Exception as e:
            return False, str(e), []

    def run_single_task(self, task_description: str) -> int:
        """Run a single task by description."""
        task = Task(
            id=1,
            title=task_description[:60],
            description=task_description
        )

        # Create a branch for safety
        branch = f"autobot-task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.setup_branch(branch)

        return self._execute_task(task)

    def run_tasks(self, tasks: list[Task], branch: str = None) -> int:
        """Run a list of tasks."""
        if not tasks:
            self.log("No tasks to run", "WARN")
            return 0

        # Setup branch
        branch = branch or f"autobot-improve-{datetime.now().strftime('%Y%m%d-%H%M')}"
        self.setup_branch(branch)

        # Initialize state
        self.state = RunnerState(
            branch=branch,
            start_time=datetime.now().isoformat(),
            tasks=tasks
        )

        self.log(f"Running {len(tasks)} tasks...")

        for i, task in enumerate(tasks):
            self.state.current_task_index = i
            self.log("")
            self.log("=" * 50)
            self.log(f"TASK {i+1}/{len(tasks)}: {task.title}")
            self.log("=" * 50)

            result = self._execute_task(task)

            if result == 0:
                self.state.completed_count += 1
            else:
                self.state.failed_count += 1
                # Stop on first failure for self-improvement (be conservative)
                if self.state.failed_count >= 2:
                    self.log("Too many failures, stopping", "ERROR")
                    break

            time.sleep(2)  # Brief pause between tasks

        # Summary
        self.log("")
        self.log("=" * 50)
        self.log("SUMMARY")
        self.log("=" * 50)
        self.log(f"Completed: {self.state.completed_count}/{len(tasks)}")
        self.log(f"Failed: {self.state.failed_count}")
        self.log(f"Branch: {branch}")

        return 0 if self.state.failed_count == 0 else 1

    def _execute_task(self, task: Task) -> int:
        """Execute a single task."""
        task.status = "in_progress"
        task.start_time = datetime.now().isoformat()

        if self.dry_run:
            self.log("[DRY RUN] Would execute task")
            task.status = "completed"
            return 0

        # Build and run prompt
        prompt = self.build_prompt(task)
        success, output, commits = self.run_aider(prompt)

        task.output = output
        task.commits = commits
        task.end_time = datetime.now().isoformat()

        if task.start_time and task.end_time:
            start = datetime.fromisoformat(task.start_time)
            end = datetime.fromisoformat(task.end_time)
            task.duration_seconds = int((end - start).total_seconds())

        if success or commits:
            task.status = "completed"
            self.log(f"Task completed ({len(commits)} commits)", "OK")
            for commit in commits[:3]:
                self.log(f"  - {commit}")
            return 0
        else:
            task.status = "failed"
            task.error = "Aider failed to complete task"
            self.log("Task failed", "ERROR")
            return 1

    def run_tasks_from_file(self, tasks_file: Path, branch: str = None) -> int:
        """Run tasks from a markdown file."""
        if not tasks_file.exists():
            self.log(f"Tasks file not found: {tasks_file}", "ERROR")
            return 1

        tasks = self._parse_tasks_file(tasks_file)
        return self.run_tasks(tasks, branch)

    def _parse_tasks_file(self, tasks_file: Path) -> list[Task]:
        """Parse tasks from markdown file."""
        content = tasks_file.read_text()
        tasks = []

        # Match ## Task N: Title or ## Title patterns
        pattern = r"##\s+(?:Task\s+\d+:\s+)?(.+?)(?=\n##|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for i, match in enumerate(matches, 1):
            lines = match.strip().split("\n", 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else title

            # Skip metadata sections
            if title.lower() in ["summary", "notes", "metadata", "config"]:
                continue

            tasks.append(Task(
                id=i,
                title=title,
                description=description
            ))

        self.log(f"Parsed {len(tasks)} tasks from {tasks_file.name}")
        return tasks


def main():
    """CLI for the task runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Autobot Task Runner")
    parser.add_argument("tasks_file", nargs="?", help="Tasks markdown file")
    parser.add_argument("--task", "-t", help="Single task to run")
    parser.add_argument("--branch", "-b", help="Git branch name")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    runner = TaskRunner(
        model=args.model,
        dry_run=args.dry_run,
        verbose=not args.quiet
    )

    if args.task:
        return runner.run_single_task(args.task)
    elif args.tasks_file:
        return runner.run_tasks_from_file(Path(args.tasks_file), args.branch)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
