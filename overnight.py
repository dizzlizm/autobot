#!/usr/bin/env python3
"""
Overnight Coding Automation with Aider + Ollama

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
DEFAULT_MODEL = "ollama/qwen2.5-coder:3b"  # Local Ollama model (no API key needed)
DEFAULT_TIMEOUT = 1800  # 30 minutes per task
MAX_RAM_PERCENT = 75  # Pause if RAM usage exceeds this
RAM_CHECK_INTERVAL = 30  # Check RAM every 30 seconds
STATE_FILE = "overnight_state.json"

# Use script directory for logs/reports
SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_DIR = SCRIPT_DIR / "logs"
REPORT_DIR = SCRIPT_DIR / "reports"
AIDER_CMD = SCRIPT_DIR / "aider"  # Use the wrapper script that activates venv
SMART_TEST = SCRIPT_DIR / "tools" / "smart-test" / "smart-test.py"  # Auto-detect testing

# Smart prompting for smaller models (3B-7B)
# Provides chain-of-thought structure and explicit guidance
SMART_PROMPT_TEMPLATE = """## Task
{title}

## Details
{description}

## Instructions
Think step-by-step:
1. First, identify which files need to be modified
2. Understand the existing code patterns in those files
3. Plan the minimal changes needed
4. Implement changes one file at a time
5. Ensure code follows existing style and conventions

## Requirements
- Make minimal, focused changes
- Follow existing code patterns in this project
- Keep the same formatting and style
- Do NOT add unnecessary comments or docstrings
- Do NOT refactor unrelated code
- Test your changes mentally before committing

Now implement the task."""


def enhance_prompt_for_small_model(title: str, description: str, model: str) -> str:
    """Wrap task in structured prompt for better small model performance.

    Smaller models (3B-7B) benefit from:
    - Clear step-by-step instructions
    - Explicit constraints
    - Chain-of-thought prompting
    """
    # Only apply enhanced prompting for small models
    is_small_model = any(size in model.lower() for size in [":3b", ":1b", ":0.5b", "-3b", "-1b"])

    if is_small_model:
        return SMART_PROMPT_TEMPLATE.format(title=title, description=description)
    else:
        # Larger models get simpler prompts
        return f"{title}\n\n{description}"


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
        test_cmd: Optional[str] = None,
        lint_cmd: Optional[str] = None,
        fix_retries: int = 2,
    ):
        self.project_path = Path(project_path).resolve()
        self.tasks_file = Path(tasks_file).resolve()
        self.branch = branch or f"overnight-{datetime.now().strftime('%Y%m%d')}"
        self.model = model
        self.timeout = timeout
        self.dry_run = dry_run
        self.resume = resume
        self.report_path = Path(report_path) if report_path else None
        self.test_cmd = test_cmd
        self.lint_cmd = lint_cmd
        self.fix_retries = fix_retries  # How many times to retry if tests fail

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

        # Check for Ollama (local models don't need API keys)
        # Only check API key if using a cloud model
        if self.model and not self.model.startswith("ollama/"):
            if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
                # Try loading from .env in script directory
                env_file = SCRIPT_DIR / ".env"
                if env_file.exists():
                    with open(env_file) as f:
                        for line in f:
                            if line.startswith("GEMINI_API_KEY="):
                                os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
                            elif line.startswith("OPENAI_API_KEY="):
                                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()

                if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
                    errors.append("No API key found (GEMINI_API_KEY or OPENAI_API_KEY) - not needed for Ollama models")

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

        # Aider output formats vary. Look for patterns like:
        # "Tokens: 12k sent, 1.5k received. Cost: $0.01"
        # "Tokens: 12,345 sent, 1,234 received"
        # We want the LAST occurrence (final totals)

        # Find all token lines and use the last one
        token_pattern = r'Tokens?:\s*([\d,.]+)(k)?\s*sent[,.]?\s*([\d,.]+)(k)?\s*(?:received|recv)'
        token_matches = list(re.finditer(token_pattern, output, re.IGNORECASE))

        if token_matches:
            match = token_matches[-1]  # Use last match
            try:
                sent_str = match.group(1).replace(',', '')
                sent_k = match.group(2)  # 'k' or None
                recv_str = match.group(3).replace(',', '')
                recv_k = match.group(4)  # 'k' or None

                sent = float(sent_str)
                recv = float(recv_str)

                if sent_k:
                    sent *= 1000
                if recv_k:
                    recv *= 1000

                usage.tokens_sent = int(sent)
                usage.tokens_received = int(recv)
            except (ValueError, AttributeError):
                pass

        # Find cost - look for last "Cost: $X.XX" pattern
        cost_pattern = r'Cost:\s*\$?([\d.]+)'
        cost_matches = list(re.finditer(cost_pattern, output, re.IGNORECASE))
        if cost_matches:
            try:
                usage.cost = float(cost_matches[-1].group(1))
            except ValueError:
                pass

        # Also check for session total which is more reliable
        session_pattern = r'(?:session|total)\s*(?:cost)?:?\s*\$?([\d.]+)'
        session_matches = list(re.finditer(session_pattern, output, re.IGNORECASE))
        if session_matches:
            try:
                session_cost = float(session_matches[-1].group(1))
                usage.cost = max(usage.cost, session_cost)
            except ValueError:
                pass

        return usage

    def run_command(self, cmd: str, description: str) -> tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        self.log(f"Running {description}: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout for tests/lint
                cwd=self.project_path
            )
            output = result.stdout + "\n" + result.stderr
            success = result.returncode == 0
            if success:
                self.log(f"{description} passed")
            else:
                self.log(f"{description} failed (exit code {result.returncode})", "WARN")
            return success, output
        except subprocess.TimeoutExpired:
            self.log(f"{description} timed out", "ERROR")
            return False, "Command timed out"
        except Exception as e:
            self.log(f"{description} error: {e}", "ERROR")
            return False, str(e)

    def run_tests(self) -> tuple[bool, str]:
        """Run the test command - auto-detects if not specified."""
        if self.test_cmd:
            return self.run_command(self.test_cmd, "Tests")
        # Auto-detect using smart-test
        if SMART_TEST.exists():
            cmd = f"python3 {SMART_TEST} test {self.project_path}"
            return self.run_command(cmd, "Tests (auto-detected)")
        return True, ""  # No test tool available

    def run_lint(self) -> tuple[bool, str]:
        """Run the lint command - auto-detects if not specified."""
        if self.lint_cmd:
            return self.run_command(self.lint_cmd, "Lint")
        # Auto-detect using smart-test
        if SMART_TEST.exists():
            cmd = f"python3 {SMART_TEST} lint {self.project_path}"
            return self.run_command(cmd, "Lint (auto-detected)")
        return True, ""  # No lint tool available

    def run_aider_fix(self, error_output: str, fix_type: str) -> bool:
        """Ask Aider to fix test/lint failures."""
        self.log(f"Asking Aider to fix {fix_type} failures...")

        # Truncate error output if too long
        if len(error_output) > 4000:
            error_output = error_output[:4000] + "\n...(truncated)"

        fix_message = f"""## Fix {fix_type.title()} Failures

## Error Output
{error_output}

## Instructions
1. Read each error message carefully
2. Identify the exact file and line number
3. Understand what the error is asking for
4. Make the minimal fix needed
5. Do NOT change unrelated code

Fix only what is broken. Keep changes minimal."""

        cmd = [
            str(AIDER_CMD),
            "--model", self.model,
            "--yes",
            "--auto-commits",
            "--no-stream",
            "--message", fix_message,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_path
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"Aider fix failed: {e}", "ERROR")
            return False

    def validate_task(self, task: Task) -> bool:
        """Run tests and lint after a task, attempt fixes if needed."""
        # Always try validation - smart-test will auto-detect if no cmds specified

        for attempt in range(self.fix_retries + 1):
            all_passed = True

            # Run lint first (usually faster)
            if self.lint_cmd:
                lint_ok, lint_output = self.run_lint()
                if not lint_ok:
                    all_passed = False
                    if attempt < self.fix_retries:
                        self.run_aider_fix(lint_output, "lint")
                        continue

            # Run tests
            if self.test_cmd:
                test_ok, test_output = self.run_tests()
                if not test_ok:
                    all_passed = False
                    if attempt < self.fix_retries:
                        self.run_aider_fix(test_output, "test")
                        continue

            if all_passed:
                if attempt > 0:
                    self.log(f"Validation passed after {attempt} fix attempts")
                return True

        self.log("Validation failed after all fix attempts", "ERROR")
        self.state.warnings.append(f"Task {task.id}: Tests/lint failed after {self.fix_retries} fix attempts")
        return False

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
        # Use smart prompting for smaller models
        message = enhance_prompt_for_small_model(task.title, task.description, self.model)

        cmd = [
            str(AIDER_CMD),  # Use wrapper script that activates venv
            "--model", self.model,
            "--yes",  # Auto-accept all prompts
            "--auto-commits",  # Auto-commit changes
            "--no-stream",  # Don't stream output (better for logs)
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
            # Run Aider with real-time output streaming
            self.log(f"Running: {' '.join(cmd[:4])}...")
            print("-" * 40)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.project_path
            )

            output_lines = []
            start = time.time()

            # Stream output in real-time
            while True:
                # Check timeout
                if time.time() - start > self.timeout:
                    process.kill()
                    raise subprocess.TimeoutExpired(cmd, self.timeout)

                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    print(f"  {line.rstrip()}")  # Show real-time
                    output_lines.append(line)

            # Get return code
            returncode = process.returncode
            task.aider_output = "".join(output_lines)
            print("-" * 40)

            # Parse usage from output
            usage = self.parse_usage(task.aider_output)
            task.tokens_sent = usage.tokens_sent
            task.tokens_received = usage.tokens_received
            task.cost = usage.cost

            # Check for commits made during this task
            new_commits = self.get_commits_since(commit_before)
            task.commits = new_commits

            if returncode == 0 or new_commits:
                # Aider completed (or made progress)
                usage_str = f", {usage.tokens_sent + usage.tokens_received:,} tokens, ${usage.cost:.4f}" if usage.tokens_sent else ""
                self.log(f"Task {task.id} aider done with {len(new_commits)} commits{usage_str}")

                if returncode != 0:
                    self.state.warnings.append(f"Task {task.id}: Aider returned non-zero exit code")

                # Run validation (tests/lint)
                if self.validate_task(task):
                    task.status = "completed"
                    self.log(f"Task {task.id} completed and validated")
                else:
                    task.status = "completed"  # Still mark complete but with warnings
                    self.log(f"Task {task.id} completed but validation failed", "WARN")
            else:
                task.status = "failed"
                task.error = f"Aider exited with code {returncode}"
                self.log(f"Task {task.id} failed: {task.error}", "ERROR")

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
        description="Overnight coding automation with Aider + Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    overnight.py --project ~/projects/web-app --tasks tasks.md

    # With tests - runs 'npm test' after each task, retries 2x if fails
    overnight.py --project ~/projects/app --tasks tasks.md --test-cmd "npm test"

    # With tests AND linting
    overnight.py --project ~/projects/app --tasks tasks.md \\
        --test-cmd "npm test" --lint-cmd "npm run lint"

    # Python project with pytest and ruff
    overnight.py --project ~/projects/api --tasks tasks.md \\
        --test-cmd "pytest" --lint-cmd "ruff check ."

    # Resume interrupted run
    overnight.py --project ~/projects/web-app --tasks tasks.md --resume

    # Dry run (no changes)
    overnight.py --project ~/projects/web-app --tasks tasks.md --dry-run
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
    parser.add_argument(
        "--test-cmd",
        help="Command to run tests after each task (e.g., 'npm test', 'pytest')"
    )
    parser.add_argument(
        "--lint-cmd",
        help="Command to run linter after each task (e.g., 'npm run lint', 'ruff check')"
    )
    parser.add_argument(
        "--fix-retries",
        type=int,
        default=2,
        help="Number of times to ask Aider to fix failing tests/lint (default: 2)"
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
        test_cmd=args.test_cmd,
        lint_cmd=args.lint_cmd,
        fix_retries=args.fix_retries,
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
