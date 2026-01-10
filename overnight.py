#!/usr/bin/env python3
"""
Overnight Coding Automation with Aider + Gemini

This script wraps Aider to enable unattended overnight coding sessions.
It handles task parsing, sequential execution, error recovery, and reporting.

Usage:
    overnight.py --project ~/projects/web-app --tasks tasks.md
    overnight.py --project ~/projects/api --tasks sprint-23.md --branch overnight-20250111
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import psutil


# Configuration
DEFAULT_MODEL = "gemini"  # Points to gemini-2.5-pro
DEFAULT_TIMEOUT = 1800  # 30 minutes per task
MAX_RAM_PERCENT = 75  # Pause if RAM usage exceeds this
RAM_CHECK_INTERVAL = 30  # Check RAM every 30 seconds
STATE_FILE = "overnight_state.json"

# Use script directory for logs/reports
SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_DIR = SCRIPT_DIR / "logs"
REPORT_DIR = SCRIPT_DIR / "reports"
AIDER_CMD = SCRIPT_DIR / "aider"  # Use the wrapper script that activates venv


@dataclass
class Usage:
    """Tracks token usage and cost."""
    tokens_sent: int = 0
    tokens_received: int = 0
    cost: float = 0.0

    def __add__(self, other):
        return Usage(
            tokens_sent=self.tokens_sent + other.tokens_sent,
            tokens_received=self.tokens_received + other.tokens_received,
            cost=self.cost + other.cost
        )


@dataclass
class Task:
    """Represents a single coding task."""
    id: int
    title: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: int = 0
    commits: list = field(default_factory=list)
    error: Optional[str] = None
    aider_output: str = ""
    tokens_sent: int = 0
    tokens_received: int = 0
    cost: float = 0.0


@dataclass
class OvernightState:
    """Tracks the state of an overnight run for crash recovery."""
    project_path: str
    tasks_file: str
    branch: str
    model: str
    start_time: str
    tasks: list = field(default_factory=list)
    current_task_index: int = 0
    total_commits: int = 0
    completed_count: int = 0
    failed_count: int = 0
    warnings: list = field(default_factory=list)


class OvernightRunner:
    """Main runner for overnight coding sessions."""

    def __init__(
        self,
        project_path: str,
        tasks_file: str,
        branch: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        dry_run: bool = False,
        resume: bool = False,
        report_path: Optional[str] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.tasks_file = Path(tasks_file).resolve()
        self.branch = branch or f"overnight-{datetime.now().strftime('%Y%m%d')}"
        self.model = model
        self.timeout = timeout
        self.dry_run = dry_run
        self.resume = resume
        self.report_path = Path(report_path) if report_path else None

        self.state: Optional[OvernightState] = None
        self.log_file: Optional[Path] = None
        self.start_time: Optional[datetime] = None

        # Ensure directories exist
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log a message to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)

        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(formatted + "\n")

    def preflight_checks(self) -> bool:
        """Run pre-flight checks before starting."""
        self.log("Running pre-flight checks...")
        errors = []

        # Check project exists and is a git repo
        if not self.project_path.exists():
            errors.append(f"Project path does not exist: {self.project_path}")
        elif not (self.project_path / ".git").exists():
            errors.append(f"Project is not a git repository: {self.project_path}")

        # Check tasks file exists
        if not self.tasks_file.exists():
            errors.append(f"Tasks file does not exist: {self.tasks_file}")

        # Check Aider wrapper exists
        if not AIDER_CMD.exists():
            errors.append(f"Aider wrapper not found at {AIDER_CMD}")

        # Check API key
        if not os.environ.get("GEMINI_API_KEY"):
            # Try loading from .env in script directory
            env_file = SCRIPT_DIR / ".env"
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
                            break

            if not os.environ.get("GEMINI_API_KEY"):
                errors.append("GEMINI_API_KEY environment variable not set")

        # Check git status (should be clean)
        os.chdir(self.project_path)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            self.log("Warning: Git working directory is not clean", "WARN")
            self.log(f"Uncommitted changes:\n{result.stdout}", "WARN")

        # Check disk space (need at least 1GB free)
        disk = psutil.disk_usage(str(self.project_path))
        if disk.free < 1_000_000_000:  # 1GB
            errors.append(f"Low disk space: {disk.free / 1_000_000_000:.2f}GB free")

        # Check RAM
        ram = psutil.virtual_memory()
        if ram.percent > MAX_RAM_PERCENT:
            self.log(f"Warning: High RAM usage: {ram.percent}%", "WARN")

        if errors:
            for error in errors:
                self.log(error, "ERROR")
            return False

        self.log("Pre-flight checks passed")
        return True

    def parse_tasks(self) -> list[Task]:
        """Parse tasks from markdown file."""
        self.log(f"Parsing tasks from {self.tasks_file}")

        with open(self.tasks_file) as f:
            content = f.read()

        tasks = []
        # Match ## Task N: Title or ## Title patterns
        task_pattern = r"##\s+(?:Task\s+\d+:\s+)?(.+?)(?=\n##|\Z)"
        matches = re.findall(task_pattern, content, re.DOTALL)

        for i, match in enumerate(matches, 1):
            lines = match.strip().split("\n", 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else title

            # Skip if it looks like a header/metadata section
            if title.lower() in ["summary", "notes", "metadata", "config"]:
                continue

            tasks.append(Task(
                id=i,
                title=title,
                description=description
            ))

        self.log(f"Found {len(tasks)} tasks")
        return tasks

    def setup_branch(self):
        """Create and checkout the overnight branch."""
        os.chdir(self.project_path)

        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True
        )
        current_branch = result.stdout.strip()

        if current_branch == self.branch:
            self.log(f"Already on branch: {self.branch}")
            return

        # Check if branch exists
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{self.branch}"],
            capture_output=True
        )

        if result.returncode == 0:
            # Branch exists, checkout
            subprocess.run(["git", "checkout", self.branch], check=True)
            self.log(f"Checked out existing branch: {self.branch}")
        else:
            # Create new branch
            subprocess.run(["git", "checkout", "-b", self.branch], check=True)
            self.log(f"Created new branch: {self.branch}")

    def wait_for_ram(self):
        """Wait if RAM usage is too high."""
        while True:
            ram = psutil.virtual_memory()
            if ram.percent < MAX_RAM_PERCENT:
                return

            self.log(f"RAM usage high ({ram.percent}%), waiting...", "WARN")
            time.sleep(RAM_CHECK_INTERVAL)

    def get_commits_since(self, since_hash: str) -> list[str]:
        """Get list of commits since a given hash."""
        result = subprocess.run(
            ["git", "log", "--oneline", f"{since_hash}..HEAD"],
            capture_output=True,
            text=True,
            cwd=self.project_path
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
        return []

    def get_current_commit(self) -> str:
        """Get current commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=self.project_path
        )
        return result.stdout.strip()

    def parse_usage(self, output: str) -> Usage:
        """Parse token usage and cost from aider output."""
        usage = Usage()

        # Match patterns like:
        # "Tokens: 12k sent, 1.5k received"
        # "Tokens: 12,345 sent, 1,234 received"
        # "Cost: $0.01"

        # Parse tokens
        token_pattern = r'Tokens?:\s*([\d,.]+)k?\s*sent,?\s*([\d,.]+)k?\s*received'
        token_match = re.search(token_pattern, output, re.IGNORECASE)
        if token_match:
            sent_str = token_match.group(1).replace(',', '')
            recv_str = token_match.group(2).replace(',', '')

            # Handle k suffix
            if 'k' in token_match.group(0).lower():
                try:
                    usage.tokens_sent = int(float(sent_str) * 1000)
                    usage.tokens_received = int(float(recv_str) * 1000)
                except ValueError:
                    pass
            else:
                try:
                    usage.tokens_sent = int(float(sent_str))
                    usage.tokens_received = int(float(recv_str))
                except ValueError:
                    pass

        # Parse cost
        cost_pattern = r'Cost:\s*\$?([\d.]+)'
        cost_match = re.search(cost_pattern, output, re.IGNORECASE)
        if cost_match:
            try:
                usage.cost = float(cost_match.group(1))
            except ValueError:
                pass

        # Also look for cumulative session cost patterns
        session_cost_pattern = r'session\s+cost:\s*\$?([\d.]+)'
        session_match = re.search(session_cost_pattern, output, re.IGNORECASE)
        if session_match:
            try:
                usage.cost = max(usage.cost, float(session_match.group(1)))
            except ValueError:
                pass

        return usage

    def run_aider_task(self, task: Task) -> bool:
        """Run Aider for a single task."""
        self.log(f"Starting task {task.id}: {task.title}")
        task.status = "in_progress"
        task.start_time = datetime.now().isoformat()

        # Get commit hash before running
        commit_before = self.get_current_commit()

        # Wait for RAM if needed
        self.wait_for_ram()

        # Build the Aider command
        # Combine title and description for the message
        message = f"{task.title}\n\n{task.description}"

        cmd = [
            str(AIDER_CMD),  # Use wrapper script that activates venv
            "--model", self.model,
            "--yes",  # Auto-accept all prompts
            "--auto-commits",  # Auto-commit changes
            "--no-stream",  # Don't stream output (better for logs)
            "--show-cost",  # Show token usage and cost
            "--message", message,
        ]

        # Add conventions file if it exists
        conventions_file = self.project_path / "CONVENTIONS.md"
        if conventions_file.exists():
            cmd.extend(["--read", str(conventions_file)])

        # Check for project-specific .aider.conf.yml
        project_config = self.project_path / ".aider.conf.yml"
        if project_config.exists():
            self.log(f"Using project config: {project_config}")

        if self.dry_run:
            self.log(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            task.status = "completed"
            task.end_time = datetime.now().isoformat()
            return True

        try:
            # Run Aider with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_path
            )

            task.aider_output = result.stdout + "\n" + result.stderr

            # Parse usage from output
            usage = self.parse_usage(task.aider_output)
            task.tokens_sent = usage.tokens_sent
            task.tokens_received = usage.tokens_received
            task.cost = usage.cost

            # Check for commits made during this task
            new_commits = self.get_commits_since(commit_before)
            task.commits = new_commits

            if result.returncode == 0:
                task.status = "completed"
                usage_str = f", {usage.tokens_sent + usage.tokens_received:,} tokens, ${usage.cost:.4f}" if usage.tokens_sent else ""
                self.log(f"Task {task.id} completed with {len(new_commits)} commits{usage_str}")
            else:
                # Aider returned non-zero but may have made partial progress
                if new_commits:
                    task.status = "completed"
                    self.log(f"Task {task.id} completed (with warnings)")
                    self.state.warnings.append(f"Task {task.id}: Aider returned non-zero exit code")
                else:
                    task.status = "failed"
                    task.error = f"Aider exited with code {result.returncode}"
                    self.log(f"Task {task.id} failed: {task.error}", "ERROR")
                    # Show aider output for debugging
                    if task.aider_output.strip():
                        self.log(f"Aider output:\n{task.aider_output[:2000]}", "DEBUG")

        except subprocess.TimeoutExpired:
            task.status = "failed"
            task.error = f"Task timed out after {self.timeout} seconds"
            self.log(f"Task {task.id} timed out", "ERROR")

            # Kill any hanging aider processes
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if 'aider' in proc.info['name'].lower():
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.log(f"Task {task.id} error: {e}", "ERROR")

        task.end_time = datetime.now().isoformat()
        if task.start_time:
            start = datetime.fromisoformat(task.start_time)
            end = datetime.fromisoformat(task.end_time)
            task.duration_seconds = int((end - start).total_seconds())

        return task.status == "completed"

    def save_state(self):
        """Save current state for crash recovery."""
        state_path = self.project_path / STATE_FILE
        with open(state_path, "w") as f:
            json.dump(asdict(self.state), f, indent=2)

    def load_state(self) -> bool:
        """Load state from previous run."""
        state_path = self.project_path / STATE_FILE
        if not state_path.exists():
            return False

        try:
            with open(state_path) as f:
                data = json.load(f)

            self.state = OvernightState(**{
                k: v for k, v in data.items()
                if k in OvernightState.__dataclass_fields__
            })

            # Reconstruct Task objects
            self.state.tasks = [
                Task(**t) for t in data.get("tasks", [])
            ]

            self.log(f"Loaded state from previous run (task {self.state.current_task_index + 1}/{len(self.state.tasks)})")
            return True
        except Exception as e:
            self.log(f"Failed to load state: {e}", "WARN")
            return False

    def clear_state(self):
        """Clear saved state after successful completion."""
        state_path = self.project_path / STATE_FILE
        if state_path.exists():
            state_path.unlink()

    def generate_report(self) -> str:
        """Generate the morning report."""
        now = datetime.now()
        duration = now - self.start_time if self.start_time else timedelta(0)

        # Count results
        completed = sum(1 for t in self.state.tasks if t.status == "completed")
        failed = sum(1 for t in self.state.tasks if t.status == "failed")
        total_commits = sum(len(t.commits) for t in self.state.tasks)

        # Calculate usage totals
        total_tokens_sent = sum(t.tokens_sent for t in self.state.tasks)
        total_tokens_received = sum(t.tokens_received for t in self.state.tasks)
        total_tokens = total_tokens_sent + total_tokens_received
        total_cost = sum(t.cost for t in self.state.tasks)

        report_lines = [
            f"# Overnight Report - {now.strftime('%Y-%m-%d')}",
            "",
            "## Summary",
            f"- **Duration**: {str(duration).split('.')[0]}",
            f"- **Tasks**: {completed}/{len(self.state.tasks)} completed",
            f"- **Commits**: {total_commits}",
            f"- **Branch**: `{self.branch}`",
            "",
            "## Usage & Cost",
            f"- **Tokens sent**: {total_tokens_sent:,}",
            f"- **Tokens received**: {total_tokens_received:,}",
            f"- **Total tokens**: {total_tokens:,}",
            f"- **Total cost**: ${total_cost:.4f}",
            "",
            "## Results",
        ]

        for task in self.state.tasks:
            status_icon = {
                "completed": "\u2705",
                "failed": "\u274c",
                "skipped": "\u23ed",
                "pending": "\u23f8",
                "in_progress": "\u25b6"
            }.get(task.status, "?")

            duration_str = ""
            if task.duration_seconds:
                mins = task.duration_seconds // 60
                secs = task.duration_seconds % 60
                duration_str = f" ({mins}m {secs}s"
                if task.commits:
                    duration_str += f", {len(task.commits)} commits"
                if task.cost > 0:
                    duration_str += f", ${task.cost:.4f}"
                duration_str += ")"

            error_info = ""
            if task.error:
                error_info = f" - {task.error}"

            report_lines.append(f"{status_icon} **Task {task.id}**: {task.title}{duration_str}{error_info}")

        # Commits section
        if total_commits > 0:
            report_lines.extend(["", "## Commits"])
            for task in self.state.tasks:
                for commit in task.commits:
                    report_lines.append(f"- `{commit}`")

        # Warnings section
        if self.state.warnings:
            report_lines.extend(["", "## Warnings"])
            for warning in self.state.warnings:
                report_lines.append(f"- {warning}")

        # Next steps
        report_lines.extend([
            "",
            "## To Review",
            f"```bash",
            f"cd {self.project_path}",
            f"git log --oneline main..{self.branch}",
            f"git diff main..{self.branch}",
            f"# Run tests",
            f"npm test  # or pytest",
            f"```",
        ])

        return "\n".join(report_lines)

    def run(self):
        """Main execution loop."""
        self.start_time = datetime.now()

        # Setup logging
        log_name = f"overnight_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file = LOG_DIR / log_name

        self.log("=" * 60)
        self.log("Overnight Coding Session Starting")
        self.log("=" * 60)
        self.log(f"Project: {self.project_path}")
        self.log(f"Tasks: {self.tasks_file}")
        self.log(f"Branch: {self.branch}")
        self.log(f"Model: {self.model}")

        # Pre-flight checks
        if not self.preflight_checks():
            self.log("Pre-flight checks failed, aborting", "ERROR")
            return 1

        # Try to resume or start fresh
        if self.resume and self.load_state():
            self.log("Resuming from previous run")
        else:
            # Parse tasks and create fresh state
            tasks = self.parse_tasks()
            if not tasks:
                self.log("No tasks found in tasks file", "ERROR")
                return 1

            self.state = OvernightState(
                project_path=str(self.project_path),
                tasks_file=str(self.tasks_file),
                branch=self.branch,
                model=self.model,
                start_time=self.start_time.isoformat(),
                tasks=tasks,
            )

        # Setup branch
        self.setup_branch()

        # Process tasks
        self.log(f"Processing {len(self.state.tasks)} tasks...")

        for i in range(self.state.current_task_index, len(self.state.tasks)):
            self.state.current_task_index = i
            task = self.state.tasks[i]

            if task.status == "completed":
                self.log(f"Skipping already completed task {task.id}")
                continue

            # Save state before each task
            self.save_state()

            success = self.run_aider_task(task)

            if success:
                self.state.completed_count += 1
                self.state.total_commits += len(task.commits)
            else:
                self.state.failed_count += 1
                self.log(f"Task {task.id} failed, continuing to next task...")

            # Save state after each task
            self.save_state()

            # Brief pause between tasks
            time.sleep(5)

        # Generate report
        self.log("Generating report...")
        report = self.generate_report()

        # Determine report path
        if self.report_path:
            report_path = self.report_path
        else:
            report_path = REPORT_DIR / f"overnight_{self.start_time.strftime('%Y%m%d')}.md"

        with open(report_path, "w") as f:
            f.write(report)

        self.log(f"Report saved to: {report_path}")

        # Calculate final usage
        total_tokens = sum(t.tokens_sent + t.tokens_received for t in self.state.tasks)
        total_cost = sum(t.cost for t in self.state.tasks)

        # Print summary
        self.log("=" * 60)
        self.log("Session Complete!")
        self.log(f"Completed: {self.state.completed_count}/{len(self.state.tasks)} tasks")
        self.log(f"Total commits: {self.state.total_commits}")
        self.log(f"Total tokens: {total_tokens:,}")
        self.log(f"Total cost: ${total_cost:.4f}")
        self.log(f"Report: {report_path}")
        self.log("=" * 60)

        # Clear state on success
        if self.state.failed_count == 0:
            self.clear_state()

        return 0 if self.state.failed_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Overnight coding automation with Aider + Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    overnight.py --project ~/projects/web-app --tasks tasks.md

    # With custom branch
    overnight.py --project ~/projects/api --tasks sprint.md --branch overnight-sprint-23

    # Resume interrupted run
    overnight.py --project ~/projects/web-app --tasks tasks.md --resume

    # Dry run (no changes)
    overnight.py --project ~/projects/web-app --tasks tasks.md --dry-run

    # Use Gemini Flash (faster, cheaper)
    overnight.py --project ~/projects/web-app --tasks tasks.md --model gemini/gemini-2.5-flash
        """
    )

    parser.add_argument(
        "--project", "-p",
        required=True,
        help="Path to the project directory"
    )
    parser.add_argument(
        "--tasks", "-t",
        required=True,
        help="Path to the tasks markdown file"
    )
    parser.add_argument(
        "--branch", "-b",
        help="Git branch name for overnight work (default: overnight-YYYYMMDD)"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Aider model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per task in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--report", "-r",
        help="Path for the output report (default: ~/reports/overnight_YYYYMMDD.md)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from a previous interrupted run"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    runner = OvernightRunner(
        project_path=args.project,
        tasks_file=args.tasks,
        branch=args.branch,
        model=args.model,
        timeout=args.timeout,
        dry_run=args.dry_run,
        resume=args.resume,
        report_path=args.report,
    )

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        print("\nInterrupted! Saving state...")
        if runner.state:
            runner.save_state()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(runner.run())


if __name__ == "__main__":
    main()
