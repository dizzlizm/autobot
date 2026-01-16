# Autobot - Self-Improving AI Agent

Autobot is an AI system that analyzes and improves **its own source code**. It uses local LLMs (via Ollama) to examine its codebase, identify improvements, generate tasks, execute changes, and learn from outcomes.

## Core Concept

Autobot focuses exclusively on self-improvement:

1. **Self-Analysis**: Examines its own Python source files to identify bugs, performance issues, and improvement opportunities
2. **Task Generation**: Converts analysis results into actionable improvement tasks
3. **Task Execution**: Uses Aider + Ollama to implement the improvements
4. **Learning**: Tracks outcomes and adjusts strategies over time

## Quick Start

```bash
# Install Ollama and pull a model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:3b

# Install Aider
pip install aider-chat

# Run self-analysis
python3 autobot.py analyze

# Run self-improvement (analyze -> generate tasks -> execute)
python3 autobot.py improve

# View learning history
python3 autobot.py history
```

## Commands

### Main CLI (`autobot.py`)

```bash
# Analyze autobot's own code for improvements
python3 autobot.py analyze
python3 autobot.py analyze --plan    # Generate improvement plan

# Run full self-improvement cycle (pure local with Ollama)
python3 autobot.py improve
python3 autobot.py improve --dry-run     # Preview without changes
python3 autobot.py improve --max-tasks 3 # Limit tasks

# Use Gemini for higher quality code execution
# Local Ollama does analysis -> Gemini 2.5 Flash writes the code
python3 autobot.py improve --gemini

# Quick self-improvement (simplified flow)
python3 autobot.py quick

# View learning history and insights
python3 autobot.py history

# Check autobot status
python3 autobot.py status

# Run a specific improvement task
python3 autobot.py run-task "Add error handling to analyzer"
```

### Direct Scripts

```bash
# Full self-modification engine
python3 self_modify.py --analyze       # Analyze codebase
python3 self_modify.py --generate-tasks # Generate task file
python3 self_modify.py --improve       # Full cycle
python3 self_modify.py --history       # Learning history

# Quick self-improvement
python3 self_improve.py                # Run quick improvement
python3 self_improve.py --dry-run      # Preview only

# Task runner
python3 runner.py tasks.md             # Run tasks from file
python3 runner.py --task "Fix bug X"   # Run single task
```

## Architecture

```
autobot/
├── autobot.py       # Main CLI entry point
├── self_modify.py   # Self-analysis and task generation engine
├── self_improve.py  # Quick self-improvement flow
├── runner.py        # Task execution engine
├── setup.sh         # Installation script
├── logs/            # Execution logs
└── reports/         # Improvement reports
```

### Components

| Module | Purpose |
|--------|---------|
| `autobot.py` | Main CLI, routes commands to appropriate handlers |
| `self_modify.py` | **SelfAnalyzer**: Examines Python files, uses Ollama to identify issues |
| | **TaskGenerator**: Converts issues into improvement tasks |
| | **LearningEngine**: Tracks outcomes, calculates success rates |
| | **SelfModifyRunner**: Orchestrates the full cycle |
| `runner.py` | **TaskRunner**: Executes tasks via Aider, manages git branches |
| `self_improve.py` | Simplified flow: read code → ask model → generate tasks → execute |

## Self-Analysis Process

When you run `autobot.py analyze`, it:

1. **Discovers files**: Finds all Python files in autobot's directory
2. **Calculates metrics**: Lines, functions, classes, TODOs per file
3. **Analyzes with Ollama**: Asks the model to identify:
   - Potential bugs
   - Performance issues
   - Code that needs refactoring
   - Missing error handling
   - Feature opportunities
4. **Prioritizes**: Sorts issues by severity (high → medium → low)
5. **Reports**: Shows top issues and optionally generates an improvement plan

## Learning Engine

Autobot tracks the outcomes of its self-improvement attempts:

```bash
python3 autobot.py history
```

Shows:
- Overall success rate
- Success rate by category (bug_fix, performance, refactor, etc.)
- Average execution time
- Total commits made
- Common failure patterns
- Suggested adjustments

The learning engine:
- Skips categories with very low success rates (< 20% after 3 attempts)
- Suggests using different models if overall success < 50%
- Recommends breaking down long-running tasks

## Requirements

- **Python 3.10+**
- **Ollama**: Local LLM runtime ([install](https://ollama.com))
- **Aider**: AI coding assistant ([install](https://aider.chat))
- **Git**: For version control

### Recommended Models

```bash
# Good balance of quality and speed (default)
ollama pull qwen2.5-coder:3b

# Higher quality, more RAM
ollama pull qwen2.5-coder:7b

# Even higher quality
ollama pull qwen2.5-coder:14b
```

## Safety Features

- **Git branches**: All changes are made on a separate branch (e.g., `autobot-improve-20250116-1430`)
- **Checkpoints**: Tags created after each successful task
- **Rollback**: Automatic rollback after multiple failures
- **Dry run**: Preview what would happen without making changes
- **Conservative limits**: Stops after 2 consecutive failures by default

## Configuration

### Model Selection

```bash
# Use a different local model
python3 autobot.py improve --model ollama/qwen2.5-coder:7b

# Or set in runner.py
DEFAULT_MODEL = "ollama/qwen2.5-coder:7b"
```

### Gemini Mode (Higher Quality)

Use `--gemini` to have Gemini 2.5 Flash write the code while local Ollama handles analysis:

```bash
# Set your API key
export GEMINI_API_KEY="your-key-here"
# Or create .env file in autobot directory:
# GEMINI_API_KEY=your-key-here

# Run with Gemini
python3 autobot.py improve --gemini
```

This hybrid approach gives you:
- **Local analysis**: Fast, free, private (Ollama)
- **Better code**: Higher quality output (Gemini 2.5 Flash)

### Analysis Model

Edit `self_modify.py`:
```python
ANALYSIS_MODEL = "ollama/qwen2.5-coder:7b"  # Default: 3b
```

## Example Session

```
$ python3 autobot.py analyze --plan

[13:45:23] ==================================================
[13:45:23] AUTOBOT SELF-ANALYSIS
[13:45:23] ==================================================
[13:45:23] Discovering source files...
[13:45:23] Found 4 source files
[13:45:24] Analyzing: autobot.py
[13:45:36] Analyzing: self_modify.py
[13:45:48] Analyzing: runner.py
[13:45:58] Analyzing: self_improve.py

[13:46:05] Files analyzed: 4
[13:46:05] Issues found: 7

Top Issues:
  1. [HIGH] Missing error handling in subprocess calls
     -> runner.py
  2. [MEDIUM] Potential race condition in task execution
     -> runner.py
  3. [MEDIUM] Unused import 'signal' could be removed
     -> autobot.py
  ...

$ python3 autobot.py improve --dry-run

[13:47:00] ==================================================
[13:47:00] AUTOBOT SELF-IMPROVEMENT
[13:47:00] ==================================================

Step 1: Self-Analysis
...

Step 2: Generate Improvement Tasks
[13:47:15] Generated 5 improvement tasks

[DRY RUN] Would execute self-improvement tasks
Tasks file: /home/user/autobot/self_improvement_tasks.md
```

## Philosophy

Autobot is designed around these principles:

1. **Self-contained**: Uses local Ollama models, no external API dependencies
2. **Focused**: Only improves itself, not general-purpose
3. **Safe**: All changes on branches, with rollback capability
4. **Learning**: Tracks outcomes to improve over time
5. **Simple**: Clear architecture, easy to understand and modify

## Contributing

Autobot can improve itself, but human contributions are welcome too:

1. Fork the repository
2. Make your changes
3. Submit a pull request

Or just run `python3 autobot.py improve` and let it try to improve itself!
