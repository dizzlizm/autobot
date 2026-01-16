#!/usr/bin/env python3
"""
Overnight Coding Automation with Aider + Ollama

This script wraps Aider to enable unattended overnight coding sessions.
It handles task parsing, sequential execution, error recovery, and reporting.

Features:
- Hybrid mode: Use Gemini for complex tasks, local Ollama for simple ones
- Prompt Loop: Ollama iteratively crafts epic prompts before sending to Gemini
  - Web search integration for best practices & documentation
  - Self-assessing loop (no artificial limits)
  - The result: Gemini receives the most comprehensive prompts possible
- Self-Modification: Autobot can analyze and improve its own source code
  - Automatic code analysis to identify bugs and improvements
  - Task generation for self-improvement
  - Learning from outcomes to get better over time

Usage:
    overnight.py --project ~/projects/web-app --tasks tasks.md
    overnight.py --project ~/projects/api --tasks sprint-23.md --branch overnight-20250111

    # Epic mode: Prompt loop + Hybrid
    overnight.py --project ~/projects/game --tasks tasks.md --hybrid --prompt-loop

    # Self-modification: Autobot improves itself
    overnight.py --self-modify
    overnight.py --self-analyze  # Just analyze, don't modify
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
import urllib.request
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import psutil


# Configuration
DEFAULT_MODEL = "ollama/qwen2.5-coder:1.5b"  # Local Ollama model (~1.5GB VRAM, fits 4GB cards easily)
SMART_MODEL = "gemini/gemini-2.5-flash"  # Cloud model for complex tasks (cheap, fast, good)
DEFAULT_TIMEOUT = 1800  # 30 minutes per task
MAX_RAM_PERCENT = 75  # Pause if RAM usage exceeds this
RAM_CHECK_INTERVAL = 30  # Check RAM every 30 seconds
STATE_FILE = "overnight_state.json"

# Keywords that indicate a task needs the smarter model
COMPLEX_TASK_KEYWORDS = [
    # Setup & Architecture
    "setup", "initialize", "init", "scaffold", "boilerplate", "architecture",
    "structure", "foundation", "core", "design", "concept",
    # Critical Systems
    "game loop", "game engine", "state management", "collision", "physics",
    "animation system", "particle system", "audio system", "sound system",
    # Complex Features
    "algorithm", "optimize", "performance", "refactor", "debug", "fix bug",
    "integration", "api", "database", "authentication", "security",
    "search", "functionality", "feature", "implement",  # New feature work
    # Creative/Design
    "creative", "invent", "original", "unique", "vision",
]

# Keywords that indicate a simple task (use cheap local model)
SIMPLE_TASK_KEYWORDS = [
    "polish", "tweak", "adjust", "minor", "small", "simple",
    "color", "style", "visual", "ui ", "button", "text",
    "add comment", "documentation", "readme", "cleanup",
    "rename", "move", "copy", "delete", "remove",
]

# Use script directory for logs/reports
SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_DIR = SCRIPT_DIR / "logs"
REPORT_DIR = SCRIPT_DIR / "reports"
AIDER_CMD = SCRIPT_DIR / "aider"  # Use the wrapper script that activates venv

# Smart prompting for smaller models (3B-7B)
# Provides chain-of-thought structure and explicit guidance
SMART_PROMPT_TEMPLATE = """## Task
{title}

## Details
{description}

## Instructions
Think step-by-step:
1. First, identify which files need to be modified or created
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

Now implement the task."""

# Prompt Loop Configuration
PROMPT_LOOP_MODEL = "ollama/qwen2.5-coder:1.5b"  # Same as DEFAULT_MODEL to avoid model swapping
PROMPT_LOOP_MAX_ITERATIONS = 20  # Safety limit (but model decides when done)
PROMPT_LOOP_TIMEOUT = 120  # Timeout per iteration in seconds


class PromptLoopEngine:
    """
    Autonomous prompt engineering engine using local Ollama.

    This engine iteratively refines prompts by:
    1. Analyzing the task requirements
    2. Searching the web for best practices, examples, documentation
    3. Enriching the prompt with technical details
    4. Self-assessing when the prompt is comprehensive enough

    The loop continues until Ollama decides the prompt is "ready" - no artificial limits.
    """

    def __init__(self, model: str = PROMPT_LOOP_MODEL, verbose: bool = True):
        self.model = model.replace("ollama/", "")  # Ollama CLI uses just model name
        self.verbose = verbose
        self.search_cache = {}  # Cache web searches
        self.iteration_history = []  # Track all iterations

    def log(self, message: str, level: str = "LOOP"):
        """Log prompt loop activity."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Use different prefixes for clarity
            prefix = {
                "LOOP": "  [LOOP]",
                "SEARCH": "    [WEB]",
                "OLLAMA": "    [OLLAMA]",
                "WARN": "  [WARN]",
                "ERROR": "  [ERROR]",
                "ASSESS": "    [ASSESS]",
            }.get(level, f"  [{level}]")
            print(f"{prefix} {timestamp} {message}")

    def web_search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Search the web using DuckDuckGo (no API key needed).
        Returns list of {title, url, snippet} dicts.
        """
        if query in self.search_cache:
            self.log(f"(cached) {query}", "SEARCH")
            return self.search_cache[query]

        self.log(f"Searching: {query}", "SEARCH")

        try:
            # Use DuckDuckGo HTML search (no API needed)
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')

            results = []
            # Parse results from DuckDuckGo HTML
            # Look for result links and snippets
            result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'

            links = re.findall(result_pattern, html)
            snippets = re.findall(snippet_pattern, html)

            for i, (link_url, title) in enumerate(links[:num_results]):
                snippet = snippets[i] if i < len(snippets) else ""
                # Clean up the URL (DuckDuckGo wraps it)
                if "uddg=" in link_url:
                    actual_url = urllib.parse.unquote(link_url.split("uddg=")[-1].split("&")[0])
                else:
                    actual_url = link_url

                results.append({
                    'title': title.strip(),
                    'url': actual_url,
                    'snippet': snippet.strip()
                })

            self.search_cache[query] = results
            self.log(f"Found {len(results)} results", "SEARCH")
            return results

        except Exception as e:
            self.log(f"Search failed: {e}", "WARN")
            return []

    def fetch_url_content(self, url: str, max_chars: int = 5000) -> str:
        """Fetch and extract text content from a URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Simple HTML to text conversion
            # Remove scripts and styles
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            return text[:max_chars]
        except Exception as e:
            self.log(f"Fetch failed for {url}: {e}", "WARN")
            return ""

    def call_ollama(self, prompt: str, system: str = None) -> str:
        """Call local Ollama model and return response."""
        cmd = ["ollama", "run", self.model]

        full_prompt = prompt
        if system:
            full_prompt = f"System: {system}\n\nUser: {prompt}"

        try:
            result = subprocess.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=PROMPT_LOOP_TIMEOUT
            )
            response = result.stdout.strip()

            # Log if something went wrong
            if result.returncode != 0:
                self.log(f"Ollama returned exit code {result.returncode}", "WARN")
                if result.stderr:
                    self.log(f"  stderr: {result.stderr[:200]}", "WARN")
            if not response:
                self.log("Ollama returned empty response", "WARN")
                if result.stderr:
                    self.log(f"  stderr: {result.stderr[:200]}", "WARN")
            elif len(response) < 50:
                self.log(f"Ollama response very short: {response[:100]}", "WARN")

            return response
        except subprocess.TimeoutExpired:
            self.log(f"Ollama call timed out after {PROMPT_LOOP_TIMEOUT}s", "WARN")
            return ""
        except Exception as e:
            self.log(f"Ollama call failed: {e}", "ERROR")
            return ""

    def analyze_task(self, title: str, description: str) -> dict:
        """Have Ollama analyze the task and identify what information would help."""
        self.log("Asking Ollama to analyze task requirements...", "OLLAMA")
        prompt = f"""Analyze this coding task and identify what additional information would make the prompt more comprehensive.

TASK TITLE: {title}

TASK DESCRIPTION:
{description}

Respond in this exact JSON format:
{{
    "task_type": "type of task (e.g., feature, bugfix, refactor, setup)",
    "technologies": ["list", "of", "relevant", "technologies"],
    "search_queries": ["specific searches to find best practices", "documentation queries", "example code searches"],
    "key_considerations": ["important things to consider", "edge cases", "potential pitfalls"],
    "missing_details": ["what details would improve this prompt"]
}}

Only respond with the JSON, no other text."""

        response = self.call_ollama(prompt)

        try:
            # Try to parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Fallback if parsing fails
        return {
            "task_type": "unknown",
            "technologies": [],
            "search_queries": [f"{title} best practices", f"{title} implementation example"],
            "key_considerations": [],
            "missing_details": []
        }

    def gather_web_knowledge(self, analysis: dict) -> str:
        """Search the web and gather relevant knowledge."""
        knowledge_parts = []

        for query in analysis.get("search_queries", [])[:5]:  # Limit to 5 searches
            results = self.web_search(query)

            if results:
                knowledge_parts.append(f"\n### Search: {query}")
                for r in results[:3]:  # Top 3 results per search
                    knowledge_parts.append(f"- **{r['title']}**: {r['snippet']}")

        # Try to fetch content from top result for each search
        for query in analysis.get("search_queries", [])[:2]:  # Deep dive on top 2
            results = self.web_search(query)
            if results and results[0].get('url'):
                url = results[0]['url']
                if not any(x in url for x in ['youtube.com', 'video', '.pdf']):
                    content = self.fetch_url_content(url, max_chars=2000)
                    if content:
                        knowledge_parts.append(f"\n### From {results[0]['title']}:")
                        knowledge_parts.append(content[:1500] + "...")

        return "\n".join(knowledge_parts) if knowledge_parts else ""

    def enhance_prompt(self, title: str, description: str, analysis: dict,
                       web_knowledge: str, iteration: int) -> str:
        """Have Ollama create an enhanced version of the prompt."""
        prompt = f"""You are an expert prompt engineer. Your job is to create the most comprehensive, detailed prompt possible for a coding AI.

ORIGINAL TASK:
Title: {title}
Description: {description}

TASK ANALYSIS:
- Type: {analysis.get('task_type', 'unknown')}
- Technologies: {', '.join(analysis.get('technologies', []))}
- Key Considerations: {', '.join(analysis.get('key_considerations', []))}

WEB RESEARCH FINDINGS:
{web_knowledge if web_knowledge else "(No web research available)"}

ITERATION: {iteration}

Create an enhanced, comprehensive prompt that:
1. Clearly states the objective
2. Includes specific technical requirements
3. Lists edge cases to handle
4. Provides implementation guidance from the research
5. Specifies quality requirements
6. Mentions best practices from the web research

The prompt should be detailed enough that ANY coding AI would produce excellent results.

Write the enhanced prompt now (just the prompt text, no meta-commentary):"""

        return self.call_ollama(prompt)

    def assess_readiness(self, original_task: str, enhanced_prompt: str, iteration: int) -> dict:
        """Have Ollama assess if the prompt is comprehensive enough."""
        prompt = f"""You are a prompt quality assessor. Evaluate if this enhanced prompt is comprehensive enough to send to a powerful AI model.

ORIGINAL TASK:
{original_task}

ENHANCED PROMPT (Iteration {iteration}):
{enhanced_prompt}

Evaluate on these criteria (1-10 each):
1. CLARITY: Is the objective crystal clear?
2. COMPLETENESS: Are all requirements specified?
3. TECHNICAL_DEPTH: Does it include enough technical details?
4. EDGE_CASES: Are edge cases and error handling mentioned?
5. GUIDANCE: Does it provide implementation direction?

Respond in this exact JSON format:
{{
    "scores": {{
        "clarity": 8,
        "completeness": 7,
        "technical_depth": 6,
        "edge_cases": 5,
        "guidance": 7
    }},
    "average_score": 6.6,
    "is_ready": false,
    "improvements_needed": ["what specific improvements would help"],
    "reasoning": "brief explanation"
}}

A prompt is "ready" when average_score >= 8.0 OR iteration >= 5 and average_score >= 7.0.
Only respond with JSON."""

        response = self.call_ollama(prompt)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                # Calculate average if not provided
                if 'scores' in result and 'average_score' not in result:
                    scores = result['scores'].values()
                    result['average_score'] = sum(scores) / len(scores)
                return result
        except json.JSONDecodeError:
            pass

        # Default: continue iterating for first few rounds
        return {
            "scores": {},
            "average_score": 5.0 if iteration < 3 else 8.0,
            "is_ready": iteration >= 3,
            "improvements_needed": [],
            "reasoning": "Could not parse assessment"
        }

    def run_loop(self, title: str, description: str) -> str:
        """
        Main prompt loop - iterate until Ollama decides the prompt is ready.

        Returns the final comprehensive prompt.
        """
        self.log(f"Starting prompt loop for: {title[:60]}...")
        self.iteration_history = []

        original_task = f"{title}\n\n{description}"
        current_prompt = original_task

        # Initial analysis
        self.log("Phase 1: Task Analysis")
        analysis = self.analyze_task(title, description)
        self.log(f"  Task type: {analysis.get('task_type', 'unknown')}")
        self.log(f"  Technologies: {', '.join(analysis.get('technologies', []) or ['general'])}")
        search_queries = analysis.get('search_queries', [])
        self.log(f"  Planned searches: {len(search_queries)}")

        # Gather web knowledge
        self.log("Phase 2: Web Research")
        web_knowledge = self.gather_web_knowledge(analysis)
        if web_knowledge:
            self.log(f"  Collected {len(web_knowledge):,} chars of research")

        self.log("Phase 3: Iterative Enhancement")
        iteration = 0
        while iteration < PROMPT_LOOP_MAX_ITERATIONS:
            iteration += 1
            self.log(f"")
            self.log(f"Iteration {iteration}/{PROMPT_LOOP_MAX_ITERATIONS}")

            # Enhance the prompt
            self.log("  Asking Ollama to enhance prompt...", "OLLAMA")
            enhanced = self.enhance_prompt(title, description, analysis, web_knowledge, iteration)

            if not enhanced or len(enhanced) < 100:
                self.log("  Enhancement failed, using previous version", "WARN")
                enhanced = current_prompt
            else:
                self.log(f"  Generated {len(enhanced):,} char prompt", "OLLAMA")

            # Assess readiness
            self.log("  Assessing prompt quality...", "ASSESS")
            assessment = self.assess_readiness(original_task, enhanced, iteration)

            avg_score = assessment.get('average_score', 0)
            is_ready = assessment.get('is_ready', False)

            self.log(f"  Quality Score: {avg_score:.1f}/10 | Ready: {'YES' if is_ready else 'NO'}", "ASSESS")

            self.iteration_history.append({
                'iteration': iteration,
                'prompt_length': len(enhanced),
                'score': avg_score,
                'is_ready': is_ready,
                'improvements': assessment.get('improvements_needed', [])
            })

            current_prompt = enhanced

            if is_ready:
                self.log(f"")
                self.log(f"Prompt READY after {iteration} iteration(s)!")
                break

            # Add improvements feedback for next iteration
            if assessment.get('improvements_needed'):
                improvements = assessment['improvements_needed'][:3]  # Show max 3
                self.log(f"  Improvements needed:", "ASSESS")
                for imp in improvements:
                    self.log(f"    - {imp[:80]}{'...' if len(imp) > 80 else ''}", "ASSESS")

                # Feed improvements back into analysis for next round
                analysis['missing_details'] = assessment['improvements_needed']

        # Final formatting
        final_prompt = self._format_final_prompt(title, current_prompt, analysis)

        self.log(f"")
        self.log(f"Phase 4: Final prompt ready ({len(final_prompt):,} chars)")
        return final_prompt

    def _format_final_prompt(self, title: str, enhanced_prompt: str, analysis: dict) -> str:
        """Format the final prompt with metadata."""
        return f"""## Task: {title}

## Comprehensive Implementation Guide

{enhanced_prompt}

## Technical Context
- Task Type: {analysis.get('task_type', 'implementation')}
- Technologies: {', '.join(analysis.get('technologies', ['general']))}

## Quality Requirements
- Follow existing code patterns and conventions
- Handle edge cases gracefully
- Write clean, maintainable code
- Test critical functionality

Now implement this task with excellence."""

    def get_stats(self) -> dict:
        """Get statistics about the prompt loop run."""
        if not self.iteration_history:
            return {}

        return {
            'total_iterations': len(self.iteration_history),
            'final_score': self.iteration_history[-1]['score'] if self.iteration_history else 0,
            'final_prompt_length': self.iteration_history[-1]['prompt_length'] if self.iteration_history else 0,
            'searches_performed': len(self.search_cache),
        }


# Special template for project setup tasks (Task 1 / initialization)
SETUP_PROMPT_TEMPLATE = """## Task
{title}

## Details
{description}

## CRITICAL: Project Setup Requirements
This is a PROJECT SETUP task. You MUST create a proper project structure:

### For JavaScript/TypeScript projects:
1. Create package.json with:
   - "name": project name (lowercase, no spaces)
   - "scripts": {{ "start": "...", "test": "echo 'Tests pass' && exit 0", "build": "..." }}
   - "dependencies": {{}} (add needed packages)
2. Create the folder structure (src/, public/, etc.)
3. Create index.html or entry point

### For Expo/React Native:
1. Use `npx create-expo-app` structure OR create:
   - package.json with expo dependencies
   - app.json with expo config
   - App.js or app/ directory
2. Include: expo, react, react-native in dependencies

### For Python:
1. Create pyproject.toml or requirements.txt
2. Create main module file
3. Create __init__.py files as needed

## Instructions
1. Determine the project type from the task description
2. Create ALL required config files (package.json, etc.)
3. Set up proper folder structure
4. Create entry point files

Now set up the project properly."""


def enhance_prompt_for_small_model(title: str, description: str, model: str, task_id: int = 0) -> str:
    """Wrap task in structured prompt for better small model performance.

    Smaller models (3B-7B) benefit from:
    - Clear step-by-step instructions
    - Explicit constraints
    - Chain-of-thought prompting
    """
    # Only apply enhanced prompting for small models
    is_small_model = any(size in model.lower() for size in [":3b", ":1b", ":0.5b", "-3b", "-1b"])

    if not is_small_model:
        # Larger models get simpler prompts
        return f"{title}\n\n{description}"

    # Check if this is a setup/initialization task
    setup_keywords = ["setup", "initialize", "init", "create project", "project structure",
                      "scaffold", "boilerplate", "initial", "task 1", "html structure"]
    is_setup_task = task_id == 1 or any(kw in title.lower() or kw in description.lower() for kw in setup_keywords)

    if is_setup_task:
        return SETUP_PROMPT_TEMPLATE.format(title=title, description=description)
    else:
        return SMART_PROMPT_TEMPLATE.format(title=title, description=description)


def select_model_for_task(task_id: int, title: str, description: str,
                          base_model: str, hybrid_mode: bool) -> tuple[str, str]:
    """Select the appropriate model for a task based on complexity.

    Returns: (model_name, reason)

    Hybrid mode strategy:
    - Task 1: Always use smart model (project setup is critical)
    - Simple tasks: Use local model (polish, colors, tweaks)
    - Complex tasks: Use smart model (features, architecture)
    - Default: Local model for cost savings
    """
    if not hybrid_mode:
        return base_model, "hybrid mode disabled"

    combined_text = f"{title} {description}".lower()

    # First task (project setup) is always critical - use smart model
    if task_id == 1:
        return SMART_MODEL, "setup task (foundation)"

    # Check for simple task keywords first (override complex if explicitly simple)
    if any(kw in combined_text for kw in SIMPLE_TASK_KEYWORDS):
        return base_model, "simple task detected"

    # Check for complex task keywords
    if any(kw in combined_text for kw in COMPLEX_TASK_KEYWORDS):
        return SMART_MODEL, "complex task detected"

    # Default to local model for cost savings
    return base_model, "default (cost savings)"


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
        hybrid_mode: bool = False,
        max_failures: int = 3,
        prompt_loop: bool = False,
        prompt_loop_model: str = PROMPT_LOOP_MODEL,
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
        self.hybrid_mode = hybrid_mode  # Use Gemini for complex, Ollama for simple
        self.max_failures = max_failures  # Stop after N consecutive failures
        self.consecutive_failures = 0  # Track consecutive failures
        self.prompt_loop = prompt_loop  # Use Ollama to craft epic prompts for Gemini
        self.prompt_loop_model = prompt_loop_model

        # Initialize prompt loop engine if enabled
        self.prompt_engine: Optional[PromptLoopEngine] = None
        if self.prompt_loop:
            self.prompt_engine = PromptLoopEngine(model=prompt_loop_model, verbose=True)

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

        # Auto-create project directory if it doesn't exist
        if not self.project_path.exists():
            self.log(f"Creating project directory: {self.project_path}")
            self.project_path.mkdir(parents=True, exist_ok=True)

        # Auto-initialize git repository if not already initialized
        if not (self.project_path / ".git").exists():
            self.log(f"Initializing git repository in: {self.project_path}")
            os.chdir(self.project_path)
            subprocess.run(["git", "init"], capture_output=True, text=True)

            # Create a basic .gitignore
            gitignore_content = """# Dependencies
node_modules/
venv/
.venv/
__pycache__/
*.pyc

# Build outputs
dist/
build/
.expo/
*.tsbuildinfo

# Environment
.env
.env.local
.env*.local

# IDE
.idea/
.vscode/
*.swp
*.swo
.DS_Store

# Logs
*.log
npm-debug.log*

# Test coverage
coverage/
.nyc_output/
"""
            gitignore_path = self.project_path / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, "w") as f:
                    f.write(gitignore_content)
                self.log("Created .gitignore")

            # Make initial commit so git branch works
            subprocess.run(["git", "add", "."], capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit - project scaffold"],
                capture_output=True, text=True
            )
            self.log("Created initial git commit")

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
        elif result.returncode != 0:
            # Git may fail on fresh repos, that's okay
            self.log("Note: Fresh git repository detected", "INFO")

        # Check for project config files (info if missing - Task 1 will create them)
        config_files = [
            "package.json",      # Node.js/JavaScript
            "pyproject.toml",    # Python (modern)
            "requirements.txt",  # Python (legacy)
            "Cargo.toml",        # Rust
            "go.mod",            # Go
            "app.json",          # Expo
        ]
        has_config = any((self.project_path / f).exists() for f in config_files)
        if not has_config:
            self.log("New project detected - Task 1 will create project structure", "INFO")

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
        """Run the test command if specified."""
        if self.test_cmd:
            return self.run_command(self.test_cmd, "Tests")
        return True, ""  # No test command specified

    def run_lint(self) -> tuple[bool, str]:
        """Run the lint command if specified."""
        if self.lint_cmd:
            return self.run_command(self.lint_cmd, "Lint")
        return True, ""  # No lint command specified

    def run_build(self) -> tuple[bool, str]:
        """Run build verification - checks for common build commands."""
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                if "build" in pkg.get("scripts", {}):
                    return self.run_command("npm run build", "Build")
            except:
                pass

        return True, ""  # No build command found, assume OK

    def create_checkpoint(self, task_id: int) -> str:
        """Create a git tag checkpoint after successful task."""
        tag_name = f"checkpoint-task-{task_id}"
        try:
            # Delete existing tag if present
            subprocess.run(
                ["git", "tag", "-d", tag_name],
                capture_output=True, cwd=self.project_path
            )
            # Create new tag
            result = subprocess.run(
                ["git", "tag", tag_name],
                capture_output=True, text=True, cwd=self.project_path
            )
            if result.returncode == 0:
                self.log(f"Created checkpoint: {tag_name}")
                return tag_name
        except Exception as e:
            self.log(f"Failed to create checkpoint: {e}", "WARN")
        return ""

    def rollback_to_checkpoint(self, task_id: int) -> bool:
        """Rollback to a previous checkpoint."""
        # Find the most recent valid checkpoint
        for check_id in range(task_id - 1, 0, -1):
            tag_name = f"checkpoint-task-{check_id}"
            result = subprocess.run(
                ["git", "rev-parse", tag_name],
                capture_output=True, cwd=self.project_path
            )
            if result.returncode == 0:
                self.log(f"Rolling back to {tag_name}...")
                subprocess.run(
                    ["git", "reset", "--hard", tag_name],
                    capture_output=True, cwd=self.project_path
                )
                self.log(f"Rolled back to checkpoint: {tag_name}")
                return True

        self.log("No checkpoint found to rollback to", "WARN")
        return False

    def get_retry_prompt(self, task: 'Task', attempt: int, error: str) -> str:
        """Generate a smarter retry prompt based on previous failure."""
        retry_hints = [
            "The previous attempt failed. Please try a DIFFERENT approach.",
            "Previous approach didn't work. Think about what went wrong and try something simpler.",
            "Multiple attempts failed. Strip down to the absolute minimum implementation.",
        ]
        hint = retry_hints[min(attempt - 1, len(retry_hints) - 1)]

        # Truncate error if too long
        if len(error) > 2000:
            error = error[:2000] + "\n...(truncated)"

        return f"""## Retry Attempt {attempt + 1}

{hint}

## Original Task
{task.title}

{task.description}

## Previous Error
{error}

## Instructions
1. Analyze what went wrong in the previous attempt
2. Consider a simpler or different approach
3. Make minimal changes that will work
4. Do NOT repeat the same mistake

Implement a working solution."""

    def run_aider_fix(self, error_output: str, fix_type: str) -> bool:
        """Ask Aider to fix test/lint failures using local model (cheaper)."""
        self.log(f"Asking local Ollama to fix {fix_type} failures...")

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

        # Always use local coder model for fixes (saves Gemini tokens)
        fix_model = DEFAULT_MODEL
        self.log(f"  Using: {fix_model}")

        cmd = [
            str(AIDER_CMD),
            "--model", fix_model,
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
        # Check if we have any validation commands
        has_lint = bool(self.lint_cmd)
        has_test = bool(self.test_cmd)

        if not has_lint and not has_test:
            return True  # No validation configured, skip silently

        for attempt in range(self.fix_retries + 1):
            all_passed = True

            # Run lint first (usually faster)
            if has_lint:
                lint_ok, lint_output = self.run_lint()
                if not lint_ok:
                    all_passed = False
                    if attempt < self.fix_retries:
                        self.run_aider_fix(lint_output, "lint")
                        continue

            # Run tests
            if has_test:
                test_ok, test_output = self.run_tests()
                if not test_ok:
                    all_passed = False
                    if attempt < self.fix_retries:
                        self.run_aider_fix(test_output, "test")
                        continue

            if all_passed:
                if attempt > 0:
                    self.log(f"  Validation passed after {attempt} fix attempts")
                return True

        self.log("Validation failed after all fix attempts", "ERROR")
        self.state.warnings.append(f"Task {task.id}: Tests/lint failed after {self.fix_retries} fix attempts")
        return False

    def run_aider_task(self, task: Task) -> bool:
        """Run Aider for a single task."""
        # Clear visual marker for new task
        print()
        self.log("=" * 60)
        self.log(f"TASK {task.id} OF {len(self.state.tasks)}: {task.title}")
        self.log("=" * 60)
        self.log(f"Description: {task.description[:200]}{'...' if len(task.description) > 200 else ''}")

        task.status = "in_progress"
        task.start_time = datetime.now().isoformat()

        # Get commit hash before running
        commit_before = self.get_current_commit()

        # Wait for RAM if needed
        self.wait_for_ram()

        # Select model based on task complexity (hybrid mode)
        task_model, model_reason = select_model_for_task(
            task.id, task.title, task.description,
            self.model, self.hybrid_mode
        )
        print()
        self.log("-" * 40)
        self.log("MODEL SELECTION")
        self.log("-" * 40)
        if self.hybrid_mode:
            self.log(f"  Mode: HYBRID (smart + local)")
            self.log(f"  Selected: {task_model}")
            self.log(f"  Reason: {model_reason}")
        else:
            self.log(f"  Mode: SINGLE MODEL")
            self.log(f"  Using: {task_model}")

        # Build the prompt - use prompt loop if enabled
        message = None

        # Use prompt loop to craft comprehensive prompts (for any model)
        if self.prompt_loop and self.prompt_engine:
            print()
            self.log("-" * 40)
            self.log("PROMPT BUILDER: Ollama Prompt Loop")
            self.log("-" * 40)
            self.log(f"  Engine: {self.prompt_loop_model}")
            self.log(f"  Strategy: Iterative refinement + web research")
            self.log(f"  Target Model: {task_model}")
            print()
            try:
                message = self.prompt_engine.run_loop(task.title, task.description)
                stats = self.prompt_engine.get_stats()
                print()
                self.log("-" * 40)
                self.log("PROMPT LOOP COMPLETE")
                self.log("-" * 40)
                self.log(f"  Iterations: {stats.get('total_iterations', 0)}")
                self.log(f"  Quality Score: {stats.get('final_score', 0):.1f}/10")
                self.log(f"  Web Searches: {stats.get('searches_performed', 0)}")
                self.log(f"  Final Prompt: {stats.get('final_prompt_length', 0):,} chars")
            except Exception as e:
                self.log(f"Prompt loop failed: {e}, falling back to standard prompt", "WARN")
                message = None

        # Fallback to standard prompting
        if message is None:
            print()
            self.log("-" * 40)
            self.log("PROMPT BUILDER: Standard Template")
            self.log("-" * 40)
            message = enhance_prompt_for_small_model(task.title, task.description, task_model, task.id)
            # Detect which template was used
            is_setup = task.id == 1 or any(kw in task.title.lower() or kw in task.description.lower()
                                           for kw in ["setup", "initialize", "init", "scaffold"])
            template_type = "Setup Template" if is_setup else "Smart Template"
            self.log(f"  Template: {template_type}")
            self.log(f"  Prompt Length: {len(message):,} chars")

        cmd = [
            str(AIDER_CMD),  # Use wrapper script that activates venv
            "--model", task_model,
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
            # Show what we're sending to the model
            print()
            self.log("-" * 40)
            self.log(f"SENDING TO: {task_model}")
            self.log("-" * 40)
            # Show first ~500 chars of the prompt as a preview
            preview_len = 500
            prompt_preview = message[:preview_len].replace('\n', '\n  ')
            self.log(f"  Prompt Preview:")
            for line in prompt_preview.split('\n')[:15]:  # Max 15 lines
                self.log(f"    {line}")
            if len(message) > preview_len:
                self.log(f"    ... ({len(message) - preview_len:,} more chars)")
            print()

            # Run Aider with real-time output streaming
            self.log("-" * 40)
            self.log(f"AIDER OUTPUT ({task_model})")
            self.log("-" * 40)

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

            # Parse usage from output
            usage = self.parse_usage(task.aider_output)
            task.tokens_sent = usage.tokens_sent
            task.tokens_received = usage.tokens_received
            task.cost = usage.cost

            # Check for commits made during this task
            new_commits = self.get_commits_since(commit_before)
            task.commits = new_commits

            # Summary of what the model did
            print()
            self.log("-" * 40)
            self.log(f"RESPONSE SUMMARY ({task_model})")
            self.log("-" * 40)
            self.log(f"  Exit Code: {returncode}")
            self.log(f"  Commits Made: {len(new_commits)}")
            for commit in new_commits[:5]:  # Show first 5 commits
                self.log(f"    - {commit}")
            if len(new_commits) > 5:
                self.log(f"    ... and {len(new_commits) - 5} more")
            if usage.tokens_sent:
                self.log(f"  Tokens Sent: {usage.tokens_sent:,}")
                self.log(f"  Tokens Received: {usage.tokens_received:,}")
                self.log(f"  Cost: ${usage.cost:.4f}")

            if returncode == 0 or new_commits:
                # Aider completed (or made progress)
                self.log(f"  Status: SUCCESS")

                if returncode != 0:
                    self.state.warnings.append(f"Task {task.id}: Aider returned non-zero exit code")

                # Run validation (tests/lint) if configured
                if self.test_cmd or self.lint_cmd:
                    print()
                    self.log("-" * 40)
                    self.log("VALIDATION")
                    self.log("-" * 40)
                    if self.test_cmd:
                        self.log(f"  Tests: {self.test_cmd}")
                    if self.lint_cmd:
                        self.log(f"  Lint: {self.lint_cmd}")

                if self.validate_task(task):
                    task.status = "completed"
                    self.log(f"  Result: PASSED")
                    self.log(f"  Task {task.id} complete!")
                else:
                    task.status = "completed"  # Still mark complete but with warnings
                    self.log(f"  Result: FAILED (but continuing)", "WARN")
            else:
                task.status = "failed"
                task.error = f"Aider exited with code {returncode}"
                self.log(f"  Status: FAILED")
                self.log(f"  Error: {task.error}", "ERROR")

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
        if self.hybrid_mode:
            self.log(f"Hybrid Mode: ON (complex={SMART_MODEL}, simple={self.model})")
        if self.prompt_loop:
            self.log(f"Prompt Loop: ON (using {self.prompt_loop_model} to craft epic prompts)")
            self.log("  -> Ollama will iterate until prompts are comprehensive")
            self.log("  -> Web search enabled for best practices & documentation")

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
        self.log(f"Max consecutive failures allowed: {self.max_failures}")

        for i in range(self.state.current_task_index, len(self.state.tasks)):
            self.state.current_task_index = i
            task = self.state.tasks[i]

            if task.status == "completed":
                self.log(f"Skipping already completed task {task.id}")
                continue

            # Check consecutive failures
            if self.consecutive_failures >= self.max_failures:
                self.log(f"Stopping: {self.consecutive_failures} consecutive failures reached limit", "ERROR")
                self.state.warnings.append(f"Stopped early: {self.consecutive_failures} consecutive failures")
                break

            # Save state before each task
            self.save_state()

            # Get commit before task for potential rollback
            commit_before_task = self.get_current_commit()

            success = self.run_aider_task(task)

            if success:
                # Verify build still works
                build_ok, build_output = self.run_build()
                if not build_ok:
                    self.log("Build broken after task, attempting rollback...", "ERROR")
                    task.error = f"Build failed: {build_output[:500]}"
                    task.status = "failed"
                    success = False

                    # Rollback to before this task
                    subprocess.run(
                        ["git", "reset", "--hard", commit_before_task],
                        capture_output=True, cwd=self.project_path
                    )
                    self.log(f"Rolled back to {commit_before_task[:8]}")

            if success:
                self.state.completed_count += 1
                self.state.total_commits += len(task.commits)
                self.consecutive_failures = 0  # Reset on success

                # Create checkpoint
                self.create_checkpoint(task.id)
            else:
                self.state.failed_count += 1
                self.consecutive_failures += 1
                self.log(f"Task {task.id} failed ({self.consecutive_failures}/{self.max_failures} consecutive)")

                # Try rollback to last checkpoint if multiple failures
                if self.consecutive_failures >= 2:
                    self.log("Multiple failures, rolling back to last checkpoint...")
                    self.rollback_to_checkpoint(task.id)

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

    # EPIC MODE: Hybrid + Prompt Loop
    # Ollama crafts comprehensive prompts -> Gemini executes with excellence
    overnight.py --project ~/projects/game --tasks tasks.md --hybrid --prompt-loop

    # Custom prompt loop model (use larger model for better prompts)
    overnight.py --project ~/projects/app --tasks tasks.md \\
        --hybrid --prompt-loop --prompt-loop-model "ollama/qwen2.5-coder:14b"

    # SELF-MODIFICATION: Analyze Autobot's own code
    overnight.py --self-analyze --project . --tasks dummy.md

    # SELF-MODIFICATION: Full self-improvement cycle
    overnight.py --self-modify --project . --tasks dummy.md

    # SELF-MODIFICATION: Dry run (see what would be done)
    overnight.py --self-modify --dry-run --project . --tasks dummy.md
        """
    )

    parser.add_argument(
        "--project", "-p",
        help="Path to the project directory (optional for --self-modify)"
    )
    parser.add_argument(
        "--tasks", "-t",
        help="Path to the tasks markdown file (optional for --self-modify)"
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
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help=f"Hybrid mode: use {SMART_MODEL} for complex tasks, local model for simple tasks (saves money)"
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=3,
        help="Stop after N consecutive task failures (default: 3)"
    )
    parser.add_argument(
        "--prompt-loop",
        action="store_true",
        help="Enable prompt loop: use local Ollama to craft epic, comprehensive prompts before sending to Gemini"
    )
    parser.add_argument(
        "--prompt-loop-model",
        default=PROMPT_LOOP_MODEL,
        help=f"Model for prompt loop (default: {PROMPT_LOOP_MODEL})"
    )
    parser.add_argument(
        "--self-modify",
        action="store_true",
        help="Self-modification mode: analyze and improve Autobot's own code"
    )
    parser.add_argument(
        "--self-analyze",
        action="store_true",
        help="Only analyze Autobot's code without making changes"
    )

    args = parser.parse_args()

    # Handle self-modification modes (don't require --project/--tasks)
    if args.self_modify or args.self_analyze:
        from self_modify import SelfModifyRunner
        self_runner = SelfModifyRunner(
            verbose=True,
            dry_run=args.dry_run,
            hybrid=args.hybrid,
            prompt_loop=args.prompt_loop
        )

        if args.self_analyze:
            # Just analyze, don't modify
            results = self_runner.analyze()
            print(f"\nAnalysis found {results.get('total_issues', 0)} issues")
            issues = results.get("issues", [])[:10]
            if issues:
                print("\nTop Issues:")
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. [{issue.get('severity', '?').upper()}] {issue.get('description', 'Unknown')[:60]}")
            sys.exit(0)
        else:
            # Full self-modification cycle
            sys.exit(self_runner.run_improvement())

    # Require --project and --tasks for normal mode
    if not args.project or not args.tasks:
        parser.error("--project and --tasks are required (unless using --self-modify)")

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
        hybrid_mode=args.hybrid,
        max_failures=args.max_failures,
        prompt_loop=args.prompt_loop,
        prompt_loop_model=args.prompt_loop_model,
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
