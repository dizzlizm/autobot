#!/usr/bin/env python3
"""
Self-Modification Engine for Autobot

Enables Autobot to analyze and improve its own source code autonomously.

Features:
- Self-Analysis: Examines its own codebase to identify issues and improvements
- Task Generation: Creates improvement tasks based on analysis
- Learning Loop: Tracks outcomes and adjusts strategies over time
- Safe Execution: Uses git branches and checkpoints for safe self-modification

Usage:
    # Analyze self and generate improvement tasks
    python3 self_modify.py --analyze

    # Run self-improvement (generates tasks then executes them)
    python3 self_modify.py --improve

    # Show learning history
    python3 self_modify.py --history
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
LEARNING_FILE = SCRIPT_DIR / "self_modify_history.json"
SELF_TASKS_FILE = SCRIPT_DIR / "self_improvement_tasks.md"
ANALYSIS_MODEL = "ollama/qwen2.5-coder:3b"  # Use local model for analysis
IMPROVEMENT_CATEGORIES = [
    "bug_fix",
    "performance",
    "new_feature",
    "refactor",
    "documentation",
    "test_coverage",
    "error_handling",
    "user_experience",
]


@dataclass
class ImprovementTask:
    """Represents a self-improvement task."""
    id: int
    category: str
    title: str
    description: str
    priority: int  # 1-5, 1 is highest
    estimated_complexity: str  # low, medium, high
    target_files: list = field(default_factory=list)
    created_at: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    outcome: str = ""


@dataclass
class LearningRecord:
    """Tracks outcomes for learning."""
    task_id: int
    task_title: str
    category: str
    success: bool
    execution_time: int  # seconds
    commits_made: int
    error_message: str = ""
    lessons_learned: list = field(default_factory=list)
    timestamp: str = ""


class SelfAnalyzer:
    """Analyzes Autobot's own source code."""

    def __init__(self, model: str = ANALYSIS_MODEL, verbose: bool = True):
        self.model = model.replace("ollama/", "")
        self.verbose = verbose
        self.source_files = []
        self.analysis_results = {}

    def log(self, message: str, level: str = "INFO"):
        """Log analysis activity."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def discover_source_files(self) -> list[Path]:
        """Find all Python source files in Autobot."""
        self.log("Discovering source files...")

        source_files = []

        # Main scripts
        for pattern in ["*.py", "tools/**/*.py"]:
            source_files.extend(SCRIPT_DIR.glob(pattern))

        # Filter out __pycache__ and test files
        source_files = [
            f for f in source_files
            if "__pycache__" not in str(f) and "test_" not in f.name
        ]

        self.source_files = source_files
        self.log(f"Found {len(source_files)} source files")
        return source_files

    def read_source(self, file_path: Path) -> str:
        """Read source file content."""
        try:
            with open(file_path) as f:
                return f.read()
        except Exception as e:
            self.log(f"Error reading {file_path}: {e}", "ERROR")
            return ""

    def call_ollama(self, prompt: str) -> str:
        """Call local Ollama model."""
        cmd = ["ollama", "run", self.model]

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.log("Ollama call timed out", "WARN")
            return ""
        except Exception as e:
            self.log(f"Ollama call failed: {e}", "ERROR")
            return ""

    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a single source file for potential improvements."""
        self.log(f"Analyzing: {file_path.name}")

        source = self.read_source(file_path)
        if not source:
            return {}

        # Calculate basic metrics
        lines = source.split('\n')
        num_lines = len(lines)
        num_functions = len(re.findall(r'^\s*def\s+\w+', source, re.MULTILINE))
        num_classes = len(re.findall(r'^\s*class\s+\w+', source, re.MULTILINE))
        num_todos = len(re.findall(r'#\s*TODO|#\s*FIXME|#\s*XXX', source, re.IGNORECASE))

        # Use Ollama for deeper analysis
        analysis_prompt = f"""Analyze this Python source file and identify potential improvements.

FILE: {file_path.name}
LINES: {num_lines}
FUNCTIONS: {num_functions}
CLASSES: {num_classes}

SOURCE CODE (first 3000 chars):
{source[:3000]}

Identify:
1. Potential bugs or error-prone code
2. Performance improvements
3. Code that could be refactored for clarity
4. Missing error handling
5. Opportunities for new features

Respond in JSON format:
{{
    "issues": [
        {{"type": "bug|performance|refactor|error_handling|feature", "severity": "low|medium|high", "description": "...", "line_hint": "approximate location"}}
    ],
    "overall_quality": 1-10,
    "summary": "brief overall assessment"
}}

Only respond with valid JSON."""

        response = self.call_ollama(analysis_prompt)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {"issues": [], "overall_quality": 7, "summary": "Analysis incomplete"}
        except json.JSONDecodeError:
            analysis = {"issues": [], "overall_quality": 7, "summary": "Failed to parse analysis"}

        analysis["metrics"] = {
            "lines": num_lines,
            "functions": num_functions,
            "classes": num_classes,
            "todos": num_todos,
        }
        analysis["file"] = str(file_path.relative_to(SCRIPT_DIR))

        return analysis

    def analyze_codebase(self) -> dict:
        """Perform full codebase analysis."""
        self.log("=" * 50)
        self.log("Starting Self-Analysis")
        self.log("=" * 50)

        self.discover_source_files()

        all_analyses = {}
        all_issues = []

        for file_path in self.source_files:
            analysis = self.analyze_file(file_path)
            if analysis:
                all_analyses[str(file_path.name)] = analysis
                for issue in analysis.get("issues", []):
                    issue["file"] = analysis.get("file", file_path.name)
                    all_issues.append(issue)

        # Sort issues by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))

        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": len(all_analyses),
            "total_issues": len(all_issues),
            "issues": all_issues,
            "file_analyses": all_analyses,
        }

        self.log("=" * 50)
        self.log(f"Analysis Complete: {len(all_issues)} issues found")
        self.log("=" * 50)

        return self.analysis_results

    def generate_improvement_plan(self) -> str:
        """Generate a strategic improvement plan using AI."""
        if not self.analysis_results:
            self.analyze_codebase()

        self.log("Generating improvement plan...")

        issues_summary = json.dumps(self.analysis_results.get("issues", [])[:20], indent=2)

        plan_prompt = f"""You are an expert software architect. Based on this codebase analysis, create a strategic improvement plan.

ANALYSIS RESULTS:
- Files analyzed: {self.analysis_results.get('files_analyzed', 0)}
- Total issues: {self.analysis_results.get('total_issues', 0)}

TOP ISSUES:
{issues_summary}

Create a prioritized improvement plan that:
1. Addresses the most critical issues first
2. Groups related changes together
3. Considers dependencies between changes
4. Balances quick wins with larger improvements

Format as a markdown task list with ## headers for each task, including:
- Clear task title
- Detailed description
- Why this improvement matters
- Which files need changes
- Any risks or considerations

Create 5-10 actionable tasks."""

        plan = self.call_ollama(plan_prompt)
        return plan if plan else "# Self-Improvement Tasks\n\n## No tasks generated\n\nAnalysis did not produce actionable improvements."


class TaskGenerator:
    """Generates self-improvement tasks from analysis."""

    def __init__(self, analyzer: SelfAnalyzer):
        self.analyzer = analyzer
        self.tasks = []

    def log(self, message: str, level: str = "INFO"):
        """Log task generation activity."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def categorize_issue(self, issue: dict) -> str:
        """Categorize an issue into improvement category."""
        issue_type = issue.get("type", "").lower()

        category_map = {
            "bug": "bug_fix",
            "performance": "performance",
            "refactor": "refactor",
            "error_handling": "error_handling",
            "feature": "new_feature",
            "documentation": "documentation",
            "test": "test_coverage",
        }

        for key, category in category_map.items():
            if key in issue_type:
                return category

        return "refactor"  # Default

    def priority_from_severity(self, severity: str) -> int:
        """Convert severity to priority (1-5)."""
        severity_map = {"high": 1, "medium": 3, "low": 5}
        return severity_map.get(severity.lower(), 3)

    def generate_tasks_from_analysis(self) -> list[ImprovementTask]:
        """Generate improvement tasks from analysis results."""
        if not self.analyzer.analysis_results:
            self.analyzer.analyze_codebase()

        self.log("Generating improvement tasks...")

        issues = self.analyzer.analysis_results.get("issues", [])
        tasks = []

        for i, issue in enumerate(issues[:15], 1):  # Limit to top 15
            task = ImprovementTask(
                id=i,
                category=self.categorize_issue(issue),
                title=f"Fix: {issue.get('description', 'Unknown issue')[:60]}",
                description=f"""Issue found in {issue.get('file', 'unknown')}:

Type: {issue.get('type', 'unknown')}
Severity: {issue.get('severity', 'unknown')}
Location: {issue.get('line_hint', 'unknown')}

Description:
{issue.get('description', 'No description')}

Requirements:
- Identify the exact location of the issue
- Implement a minimal, focused fix
- Ensure no regression in existing functionality
- Follow existing code patterns""",
                priority=self.priority_from_severity(issue.get("severity", "medium")),
                estimated_complexity=issue.get("severity", "medium"),
                target_files=[issue.get("file", "")],
                created_at=datetime.now().isoformat(),
            )
            tasks.append(task)

        self.tasks = tasks
        self.log(f"Generated {len(tasks)} improvement tasks")
        return tasks

    def generate_tasks_file(self, output_path: Optional[Path] = None) -> Path:
        """Generate a tasks.md file for runner.py to consume."""
        if not self.tasks:
            self.generate_tasks_from_analysis()

        output_path = output_path or SELF_TASKS_FILE

        lines = [
            "# Self-Improvement Tasks",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total Tasks: {len(self.tasks)}",
            "",
            "---",
            "",
        ]

        # Group by priority
        for priority in range(1, 6):
            priority_tasks = [t for t in self.tasks if t.priority == priority]
            if priority_tasks:
                priority_name = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Minor"}.get(priority, "Other")
                lines.append(f"# Priority: {priority_name}")
                lines.append("")

                for task in priority_tasks:
                    lines.append(f"## Task {task.id}: {task.title}")
                    lines.append("")
                    lines.append(f"**Category**: {task.category}")
                    lines.append(f"**Complexity**: {task.estimated_complexity}")
                    lines.append(f"**Target Files**: {', '.join(task.target_files)}")
                    lines.append("")
                    lines.append(task.description)
                    lines.append("")
                    lines.append("---")
                    lines.append("")

        content = "\n".join(lines)

        with open(output_path, "w") as f:
            f.write(content)

        self.log(f"Tasks file written to: {output_path}")
        return output_path


class LearningEngine:
    """Tracks outcomes and learns from self-improvement attempts."""

    def __init__(self, history_file: Path = LEARNING_FILE):
        self.history_file = history_file
        self.records: list[LearningRecord] = []
        self.load_history()

    def log(self, message: str, level: str = "INFO"):
        """Log learning activity."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_history(self):
        """Load learning history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                self.records = [
                    LearningRecord(**r) for r in data.get("records", [])
                ]
                self.log(f"Loaded {len(self.records)} learning records")
            except Exception as e:
                self.log(f"Failed to load history: {e}", "WARN")
                self.records = []
        else:
            self.records = []

    def save_history(self):
        """Save learning history to file."""
        data = {
            "updated_at": datetime.now().isoformat(),
            "total_records": len(self.records),
            "records": [asdict(r) for r in self.records],
        }

        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)

        self.log(f"Saved {len(self.records)} learning records")

    def record_outcome(self, task: ImprovementTask, success: bool,
                       execution_time: int, commits: int, error: str = ""):
        """Record the outcome of a self-improvement task."""
        record = LearningRecord(
            task_id=task.id,
            task_title=task.title,
            category=task.category,
            success=success,
            execution_time=execution_time,
            commits_made=commits,
            error_message=error,
            timestamp=datetime.now().isoformat(),
        )

        self.records.append(record)
        self.save_history()

        self.log(f"Recorded outcome: {task.title[:40]}... -> {'SUCCESS' if success else 'FAILED'}")

    def get_success_rate(self, category: Optional[str] = None) -> float:
        """Calculate success rate, optionally by category."""
        if not self.records:
            return 0.0

        relevant = self.records
        if category:
            relevant = [r for r in self.records if r.category == category]

        if not relevant:
            return 0.0

        successes = sum(1 for r in relevant if r.success)
        return successes / len(relevant)

    def get_insights(self) -> dict:
        """Generate insights from learning history."""
        if not self.records:
            return {"message": "No learning history yet"}

        insights = {
            "total_attempts": len(self.records),
            "overall_success_rate": self.get_success_rate(),
            "by_category": {},
            "average_execution_time": sum(r.execution_time for r in self.records) / len(self.records),
            "total_commits": sum(r.commits_made for r in self.records),
        }

        # Success rate by category
        for category in IMPROVEMENT_CATEGORIES:
            category_records = [r for r in self.records if r.category == category]
            if category_records:
                insights["by_category"][category] = {
                    "attempts": len(category_records),
                    "success_rate": self.get_success_rate(category),
                }

        # Find problematic patterns
        failed_records = [r for r in self.records if not r.success]
        if failed_records:
            error_patterns = {}
            for r in failed_records:
                if r.error_message:
                    # Extract key error type
                    error_key = r.error_message[:50]
                    error_patterns[error_key] = error_patterns.get(error_key, 0) + 1

            insights["common_failures"] = sorted(
                error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

        return insights

    def should_skip_category(self, category: str) -> bool:
        """Determine if a category should be skipped based on learning."""
        rate = self.get_success_rate(category)
        category_records = [r for r in self.records if r.category == category]

        # Skip if low success rate with sufficient data
        if len(category_records) >= 3 and rate < 0.2:
            self.log(f"Skipping {category}: low success rate ({rate:.0%})", "WARN")
            return True

        return False

    def suggest_adjustments(self) -> list[str]:
        """Suggest adjustments based on learning history."""
        suggestions = []
        insights = self.get_insights()

        if insights.get("overall_success_rate", 1) < 0.5:
            suggestions.append("Consider using a more capable model for complex tasks")

        for category, data in insights.get("by_category", {}).items():
            if data.get("success_rate", 1) < 0.3 and data.get("attempts", 0) >= 2:
                suggestions.append(f"Category '{category}' has low success - may need human review")

        if insights.get("average_execution_time", 0) > 600:
            suggestions.append("Tasks taking too long - consider breaking into smaller chunks")

        return suggestions

    def print_history(self):
        """Print formatted learning history."""
        insights = self.get_insights()

        print("\n" + "=" * 60)
        print("SELF-IMPROVEMENT LEARNING HISTORY")
        print("=" * 60)

        print(f"\nTotal Attempts: {insights.get('total_attempts', 0)}")
        print(f"Overall Success Rate: {insights.get('overall_success_rate', 0):.1%}")
        print(f"Total Commits Made: {insights.get('total_commits', 0)}")
        print(f"Average Execution Time: {insights.get('average_execution_time', 0):.0f}s")

        print("\nBy Category:")
        for category, data in insights.get("by_category", {}).items():
            print(f"  {category}: {data.get('success_rate', 0):.0%} ({data.get('attempts', 0)} attempts)")

        suggestions = self.suggest_adjustments()
        if suggestions:
            print("\nSuggested Adjustments:")
            for s in suggestions:
                print(f"  - {s}")

        print("\n" + "=" * 60)


class SelfModifyRunner:
    """Main runner for self-modification."""

    def __init__(self, verbose: bool = True, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.analyzer = SelfAnalyzer(verbose=verbose)
        self.task_generator = TaskGenerator(self.analyzer)
        self.learning = LearningEngine()

    def log(self, message: str, level: str = "INFO"):
        """Log runner activity."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def analyze(self) -> dict:
        """Run self-analysis."""
        return self.analyzer.analyze_codebase()

    def generate_tasks(self) -> Path:
        """Generate self-improvement tasks."""
        return self.task_generator.generate_tasks_file()

    def run_improvement(self, max_tasks: int = 5) -> int:
        """Run self-improvement cycle."""
        self.log("=" * 60)
        self.log("SELF-IMPROVEMENT CYCLE")
        self.log("=" * 60)

        # Step 1: Analyze
        self.log("\nStep 1: Self-Analysis")
        self.analyze()

        # Step 2: Generate tasks
        self.log("\nStep 2: Generate Improvement Tasks")
        tasks_file = self.generate_tasks()

        if self.dry_run:
            self.log("\n[DRY RUN] Would execute self-improvement tasks")
            self.log(f"Tasks file: {tasks_file}")
            return 0

        # Step 3: Execute via runner.py
        self.log("\nStep 3: Execute Self-Improvement")

        # Create a safe branch for self-modification
        branch = f"autobot-improve-{datetime.now().strftime('%Y%m%d-%H%M')}"

        # Use the new focused runner
        from runner import TaskRunner

        runner = TaskRunner(
            project_path=str(SCRIPT_DIR),
            dry_run=self.dry_run,
            verbose=True
        )

        self.log(f"Running tasks from: {tasks_file}")
        self.log(f"Branch: {branch}")

        try:
            result = runner.run_tasks_from_file(tasks_file, branch)

            success = result == 0
            self.log(f"Self-improvement {'completed successfully' if success else 'had failures'}")

            return result

        except Exception as e:
            self.log(f"Self-improvement failed: {e}", "ERROR")
            return 1

    def show_history(self):
        """Display learning history."""
        self.learning.print_history()


def main():
    parser = argparse.ArgumentParser(
        description="Self-Modification Engine for Autobot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze autobot's codebase and show issues
    python3 self_modify.py --analyze

    # Generate improvement tasks file
    python3 self_modify.py --generate-tasks

    # Run full self-improvement cycle
    python3 self_modify.py --improve

    # Dry run (show what would happen)
    python3 self_modify.py --improve --dry-run

    # Show learning history
    python3 self_modify.py --history

Note: Use 'python3 autobot.py' for the main CLI interface.
"""
    )

    parser.add_argument(
        "--analyze", "-a",
        action="store_true",
        help="Analyze codebase and show potential improvements"
    )
    parser.add_argument(
        "--generate-tasks", "-g",
        action="store_true",
        help="Generate self-improvement tasks file"
    )
    parser.add_argument(
        "--improve", "-i",
        action="store_true",
        help="Run full self-improvement cycle"
    )
    parser.add_argument(
        "--history", "-H",
        action="store_true",
        help="Show learning history and insights"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    runner = SelfModifyRunner(
        verbose=not args.quiet,
        dry_run=args.dry_run
    )

    if args.history:
        runner.show_history()
        return 0

    if args.analyze:
        results = runner.analyze()
        print(f"\nAnalysis found {results.get('total_issues', 0)} issues across {results.get('files_analyzed', 0)} files")

        # Show top issues
        issues = results.get("issues", [])[:10]
        if issues:
            print("\nTop Issues:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. [{issue.get('severity', '?').upper()}] {issue.get('description', 'Unknown')[:60]}")
                print(f"     File: {issue.get('file', 'unknown')}")
        return 0

    if args.generate_tasks:
        tasks_file = runner.generate_tasks()
        print(f"\nTasks written to: {tasks_file}")
        return 0

    if args.improve:
        return runner.run_improvement()

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
