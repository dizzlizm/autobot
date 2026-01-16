# Quicknote CLI - Test POC Tasks

A simple Python CLI tool that saves notes to a JSON file.

## Set up project structure
Create a Python CLI tool called "quicknote" that saves notes to a JSON file.
- Create main.py with argparse for CLI interface
- Create notes.py for note storage logic (add, list, delete notes)
- Create a basic README.md with usage instructions
- Notes should be stored in ~/.quicknote/notes.json
- Each note should have: id, content, timestamp, tags (optional)

## Add search functionality
Add ability to search notes by keyword.
- Add a `search` subcommand to the CLI
- Case-insensitive search across note content
- Return matching notes with timestamps formatted nicely
- Support searching by tag with --tag flag
- Show "No notes found" message when no matches

## Add color output
Make the CLI output colorful using simple ANSI codes (no external dependencies).
- Green for success messages (note added, deleted)
- Yellow for warnings (no notes found, search returned 0 results)
- Cyan for note IDs and timestamps
- Notes list displayed nicely with borders
- Keep it simple - just use ANSI escape codes directly
