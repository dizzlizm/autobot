# Autobot - Overnight Coding Automation

Automated overnight coding using [Aider](https://aider.chat). Queue up tasks, go to sleep, wake up to commits and a report.

## What It Does

`overnight.py` runs Aider in a loop over your task list:

1. Parses tasks from a markdown file
2. Runs each task through Aider
3. Auto-commits changes
4. Generates a morning report

## Usage

```bash
# Basic usage
./overnight.py --project ~/projects/my-app --tasks tasks.md

# With validation (runs tests/lint after each task)
./overnight.py --project ~/projects/my-app --tasks tasks.md \
    --test-cmd "npm test" --lint-cmd "npm run lint"

# Hybrid mode: Gemini for complex tasks, local Ollama for simple ones
./overnight.py --project ~/projects/my-app --tasks tasks.md --hybrid

# Epic mode: Local Ollama crafts comprehensive prompts, then Gemini executes
./overnight.py --project ~/projects/my-app --tasks tasks.md --hybrid --prompt-loop

# Resume an interrupted run
./overnight.py --project ~/projects/my-app --tasks tasks.md --resume

# Dry run (see what would happen)
./overnight.py --project ~/projects/my-app --tasks tasks.md --dry-run
```

## Options

| Flag | Description |
|------|-------------|
| `--project`, `-p` | Path to project directory (required) |
| `--tasks`, `-t` | Path to tasks markdown file (required) |
| `--branch`, `-b` | Git branch for overnight work (default: `overnight-YYYYMMDD`) |
| `--model`, `-m` | Aider model (default: `ollama/qwen2.5-coder:3b`) |
| `--timeout` | Timeout per task in seconds (default: 1800) |
| `--test-cmd` | Command to run tests after each task |
| `--lint-cmd` | Command to run linter after each task |
| `--fix-retries` | Times to retry fixing test/lint failures (default: 2) |
| `--hybrid` | Use Gemini for complex tasks, local model for simple ones |
| `--prompt-loop` | Use Ollama to craft better prompts before sending to Gemini |
| `--max-failures` | Stop after N consecutive failures (default: 3) |
| `--resume` | Resume from a previous interrupted run |
| `--dry-run` | Show what would happen without making changes |
| `--report`, `-r` | Custom path for output report |

## Task File Format

Create a markdown file with `##` headings for each task:

```markdown
## Set up project structure

Create a React app with:
- src/ directory with components/
- Basic App component
- package.json with scripts

## Add user authentication

Implement login/logout with:
- Login form component
- Auth context for state
- Protected route wrapper

## Fix the date picker bug

The date picker in src/components/DatePicker.tsx
doesn't handle timezone conversion correctly.
```

Tasks are processed in order. Be specific about what you want.

## Modes

### Default Mode
Uses a local Ollama model (`ollama/qwen2.5-coder:3b`) for all tasks. Free, runs offline.

### Hybrid Mode (`--hybrid`)
Automatically selects the right model per task:
- **Gemini** (`gemini/gemini-3-pro-preview`): First 3 tasks, setup, architecture, complex features
- **Local Ollama**: Polish, tweaks, simple changes

```bash
./overnight.py --project ~/myapp --tasks tasks.md --hybrid
```

### Prompt Loop Mode (`--prompt-loop`)
Uses local Ollama to iteratively craft comprehensive prompts before sending to any model:

1. Analyzes the task requirements
2. Searches the web for best practices
3. Enhances the prompt through multiple iterations
4. Self-assesses quality (continues until score >= 8/10)
5. Sends the refined prompt to the target model

Works with any mode:
```bash
# With hybrid (Gemini + Ollama)
./overnight.py --project ~/myapp --tasks tasks.md --hybrid --prompt-loop

# With just local Ollama (all tasks get enhanced prompts)
./overnight.py --project ~/myapp --tasks tasks.md --prompt-loop
```

## Validation

Validation runs automatically after each task using smart-test (auto-detects your project type). You can also specify explicit commands.

What happens:
1. Runs lint check after each task
2. Runs tests after each task
3. If they fail, asks Aider to fix the issues
4. Retries up to `--fix-retries` times (default: 2)
5. Continues to next task even if validation fails (with warnings)

```bash
# Auto-detect (uses smart-test) - just works
./overnight.py --project ~/myapp --tasks tasks.md

# Or specify explicit commands
./overnight.py --project ~/myapp --tasks tasks.md \
    --test-cmd "npm test" --lint-cmd "npm run lint"
```

## Reports

After each run, a report is saved to `reports/overnight_YYYYMMDD.md`:

```markdown
# Overnight Report - 2025-01-11

## Summary
- Duration: 2:45:30
- Tasks: 4/5 completed
- Commits: 12
- Branch: `overnight-20250111`

## Usage & Cost
- Tokens sent: 45,230
- Tokens received: 12,100
- Total cost: $0.1234

## Results
- Task 1: Set up project structure (15m, 3 commits, $0.02)
- Task 2: Add user authentication (45m, 5 commits, $0.05)
- Task 3: Fix date picker bug (20m, 2 commits, $0.01)
- Task 4: Add dashboard (1h, 2 commits, $0.04)
- Task 5: Email integration - Aider exited with code 1
```

## Safety Features

- **Checkpoints**: Creates git tags after each successful task
- **Rollback**: Rolls back to last checkpoint after multiple failures
- **State recovery**: Saves progress to `overnight_state.json` for resume
- **RAM monitoring**: Pauses if RAM usage exceeds 75%
- **Timeouts**: Kills tasks that run too long (default 30 min)
- **Max failures**: Stops after N consecutive failures (default 3)

## Configuration

### API Keys

For Gemini (hybrid/cloud mode):
```bash
export GEMINI_API_KEY="your-key"
# Or create .env file in this directory
```

For Ollama (default/local mode):
```bash
# Install Ollama: https://ollama.ai
ollama pull qwen2.5-coder:3b
```

### Project Context

Create `CONVENTIONS.md` in your project to give Aider context:

```markdown
# My App

## Stack
- React 18 + TypeScript
- Tailwind CSS
- Vite

## Commands
- `npm run dev` - Start dev server
- `npm test` - Run tests

## Rules
- Use functional components
- All functions need TypeScript types
- No inline styles
```

## Directory Structure

```
autobot/
├── overnight.py      # Main script
├── aider             # Aider wrapper (activates venv)
├── logs/             # Run logs
├── reports/          # Morning reports
├── templates/        # Task file templates
│   ├── tasks.md
│   ├── CONVENTIONS.md
│   └── .aider.conf.yml
├── tools/
│   └── smart-test/   # Auto-detect test/lint commands
└── systemd/          # For scheduled runs
```

## Scheduled Runs

Use the systemd units to run overnight automatically:

```bash
# Install
./systemd/install-systemd.sh

# Configure your project in the service file
# Enable timer (runs at 11 PM)
systemctl --user enable overnight-coder.timer
systemctl --user start overnight-coder.timer
```

## Troubleshooting

**Aider not found**: Make sure the `aider` wrapper script exists and your venv is set up.

**Task times out**: Increase with `--timeout 3600` (1 hour).

**RAM pausing too often**: Edit `MAX_RAM_PERCENT` in overnight.py (default 75%).

**Bad edits**: Make your task descriptions more specific, add CONVENTIONS.md.

**API errors**: Check your GEMINI_API_KEY. For local-only, use the default Ollama model.
