# Overnight Coding Automation with Aider + Gemini

Automated overnight coding using [Aider](https://aider.chat) with Google's Gemini API. Run multiple coding tasks while you sleep, wake up to a detailed report.

## Quick Start

```bash
# 1. Run setup (installs Aider, configures Gemini)
./setup.sh

# 2. Source shell config for aliases
source ~/.bashrc

# 3. Create tasks file
cp templates/tasks.md ~/projects/my-app/tasks.md
# Edit tasks.md with your tasks

# 4. Add project context (optional but recommended)
cp templates/CONVENTIONS.md ~/projects/my-app/
# Customize CONVENTIONS.md for your project

# 5. Run overnight
./overnight.py --project ~/projects/my-app --tasks ~/projects/my-app/tasks.md

# 6. Check results in the morning
cat ~/reports/overnight_$(date +%Y%m%d).md
```

## Directory Structure

```
~/
├── overnight/
│   ├── overnight.py       # Main runner script
│   ├── setup.sh           # Installation script
│   ├── templates/
│   │   ├── CONVENTIONS.md # Project context template
│   │   ├── tasks.md       # Task file template
│   │   └── .aider.conf.yml
│   ├── systemd/           # Systemd units for scheduling
│   └── logs/              # Run logs
├── reports/               # Morning reports
└── projects/              # Your projects
    └── my-app/
        ├── CONVENTIONS.md # Project-specific context
        ├── tasks.md       # Overnight tasks
        └── .aider.conf.yml
```

## Usage

### Interactive Mode (Testing)

```bash
# Quick test with a single task
cd ~/projects/my-app
aider --model gemini --yes --message "Add a login feature"

# Or use the alias
aider-quick "Add a login feature"
```

### Overnight Mode

```bash
# Basic usage
./overnight.py --project ~/projects/my-app --tasks tasks.md

# With custom branch name
./overnight.py --project ~/projects/api --tasks tasks.md --branch overnight-sprint-23

# With custom report path
./overnight.py --project ~/projects/app --tasks tasks.md --report ~/reports/sprint23.md

# Resume interrupted run
./overnight.py --project ~/projects/app --tasks tasks.md --resume

# Dry run (show what would happen)
./overnight.py --project ~/projects/app --tasks tasks.md --dry-run

# Use faster/cheaper model
./overnight.py --project ~/projects/app --tasks tasks.md --model gemini/gemini-2.5-flash

# Custom timeout per task (in seconds)
./overnight.py --project ~/projects/app --tasks tasks.md --timeout 3600
```

### Scheduled Runs (systemd)

```bash
# Install systemd units
./systemd/install-systemd.sh

# Edit service to set your project
nano ~/.config/systemd/user/overnight-coder.service

# Enable timer (runs at 11 PM daily)
systemctl --user enable overnight-coder.timer
systemctl --user start overnight-coder.timer

# Check status
systemctl --user list-timers
systemctl --user status overnight-coder.timer
```

## Configuration

### Gemini API Key

Set your API key in one of these places:

```bash
# Option 1: Environment variable (in ~/.bashrc)
export GEMINI_API_KEY="your-key-here"

# Option 2: In ~/overnight/.env
echo "GEMINI_API_KEY=your-key-here" > ~/overnight/.env
chmod 600 ~/overnight/.env
```

Get a free API key at: https://aistudio.google.com/app/apikey

### Model Selection

| Model | Speed | Cost | Use For |
|-------|-------|------|---------|
| `gemini` | Fast | $$ | Default, best quality |
| `gemini-exp` | Fast | Free* | Testing, free tier |
| `gemini/gemini-2.5-flash` | Faster | $ | Quick tasks |

*Free tier has usage limits

### Project Configuration

Create `.aider.conf.yml` in your project root:

```yaml
model: gemini
auto-commits: true
read:
  - CONVENTIONS.md
  - docs/architecture.md
stream: false
```

See `templates/.aider.conf.yml` for all options.

## Task File Format

Tasks are defined in markdown with `##` headings:

```markdown
# Overnight Tasks

## Add user authentication

Implement JWT-based authentication with:
- /api/auth/register endpoint
- /api/auth/login endpoint
- Auth middleware for protected routes
- Tests for all endpoints

## Fix issue #42

The form validation isn't showing errors.
See src/components/Form.tsx

## Improve test coverage

Add tests for userService.ts:
- createUser() success and error cases
- updateUser() validation
```

**Tips:**
- Be specific about requirements
- Mention relevant files when known
- Order tasks logically (dependencies first)
- Include acceptance criteria

## Project Context (CONVENTIONS.md)

Provide project context so Aider makes better decisions:

```markdown
# Project: my-app

## Tech Stack
- Frontend: React + TypeScript
- Backend: FastAPI + Python
- Database: PostgreSQL

## Commands
- `npm run dev` - Start frontend
- `pytest` - Run tests

## Standards
- All functions need type annotations
- Use conventional commits
- Write tests for new features

## Don't Touch
- .env files
- migrations/
```

## Morning Report

After each run, a report is generated:

```markdown
# Overnight Report - 2025-01-11

## Summary
- Duration: 6h 23m
- Tasks: 4/5 completed
- Commits: 8

## Results
✅ Task 1: User authentication (2h 15m, 3 commits)
✅ Task 2: Dashboard API (1h 30m, 2 commits)
✅ Task 3: Fix issue #42 (45m, 1 commit)
❌ Task 5: Email integration - BLOCKED (missing SMTP config)

## Commits
- abc123: feat: add user registration
- def456: feat: add login endpoint
...
```

## Features

### Pre-flight Checks
- Verifies git repo is clean
- Checks API key is configured
- Validates disk space (>1GB)
- Monitors RAM usage

### Error Recovery
- Saves state after each task
- Resume with `--resume` flag
- Continues to next task on failure

### Resource Monitoring
- Pauses when RAM > 75%
- Configurable timeouts per task
- Kills hanging processes

### Crash Recovery
State is saved to `overnight_state.json` in the project. Resume with:
```bash
./overnight.py --project ~/projects/app --tasks tasks.md --resume
```

## Troubleshooting

### "GEMINI_API_KEY not set"
```bash
# Check if key is set
echo $GEMINI_API_KEY

# Set it
export GEMINI_API_KEY="your-key"
# Or add to ~/overnight/.env
```

### "Aider not found"
```bash
# Reinstall
pipx install aider-chat
pipx inject aider-chat google-generativeai

# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Task times out
Increase timeout:
```bash
./overnight.py --project ... --tasks ... --timeout 7200  # 2 hours
```

### High RAM usage pausing too often
Edit `overnight.py` and change `MAX_RAM_PERCENT`:
```python
MAX_RAM_PERCENT = 85  # Allow higher usage
```

### Aider making bad edits
1. Make your CONVENTIONS.md more specific
2. Use more detailed task descriptions
3. Review and iterate on prompts

## Aider Command Reference

```bash
# Basic interactive mode
aider --model gemini

# Single task (non-interactive)
aider --model gemini --yes --message "your task"

# With conventions file
aider --model gemini --read CONVENTIONS.md

# List available models
aider --list-models gemini/
```

Key flags for overnight use:
- `--yes` - Auto-accept prompts
- `--auto-commits` - Commit after changes
- `--message "task"` - Run single task then exit
- `--no-stream` - Don't stream output
- `--read FILE` - Load context file (read-only)

## Links

- [Aider Documentation](https://aider.chat/docs/)
- [Aider Scripting Guide](https://aider.chat/docs/scripting.html)
- [Gemini API](https://ai.google.dev/gemini-api/docs)
- [Get Gemini API Key](https://aistudio.google.com/app/apikey)
