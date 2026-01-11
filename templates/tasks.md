# Overnight Tasks - [DATE]

> Instructions for creating task files:
> - Each ## heading becomes a task
> - Tasks run sequentially, so order them logically
> - **CRITICAL**: Task 1 MUST set up project structure for new projects
> - Be specific - small models need explicit instructions
> - Include file paths when known

---

<!--
=============================================================================
TASK 1 EXAMPLES - Choose ONE based on your project type
These are CRITICAL for new projects - the AI needs explicit setup instructions
=============================================================================
-->

## Task 1 Example: Web Game (Vanilla JS)

Set up a vanilla JavaScript web game project:

1. Create package.json:
```json
{
  "name": "my-game",
  "scripts": {
    "start": "npx serve .",
    "test": "echo 'Tests pass' && exit 0"
  }
}
```

2. Create index.html with:
   - HTML5 doctype
   - Canvas element (800x600)
   - Script tag loading game.js

3. Create game.js with:
   - Canvas context setup
   - Basic game loop (requestAnimationFrame)
   - Empty init() function

4. Create styles.css with basic canvas centering

---

## Task 1 Example: Expo Mobile App

Set up an Expo React Native project:

1. Create package.json:
```json
{
  "name": "my-app",
  "main": "expo-router/entry",
  "scripts": {
    "start": "expo start",
    "test": "echo 'Tests pass' && exit 0"
  },
  "dependencies": {
    "expo": "~50.0.0",
    "expo-router": "~3.4.0",
    "react": "18.2.0",
    "react-native": "0.73.0",
    "react-native-safe-area-context": "4.8.2"
  }
}
```

2. Create app.json with expo config (name, slug, version)

3. Create app/_layout.tsx with Stack navigator

4. Create app/index.tsx with basic screen using View/Text

---

## Task 1 Example: Node.js API

Set up a Node.js Express API project:

1. Create package.json:
```json
{
  "name": "my-api",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "test": "echo 'Tests pass' && exit 0"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

2. Create src/index.js with:
   - Express app setup
   - Health check route GET /health
   - Listen on port 3000

3. Create src/routes/ directory

---

## Task 1 Example: Python Project

Set up a Python project:

1. Create pyproject.toml:
```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.10"

[project.scripts]
start = "python -m myproject"
```

2. Create myproject/__init__.py

3. Create myproject/main.py with entry point

4. Create tests/ directory with test_main.py

---

<!--
=============================================================================
FEATURE TASK EXAMPLES - Use these patterns for subsequent tasks
=============================================================================
-->

## Add user authentication

Implement JWT-based authentication with the following:

1. Create a `/api/auth/register` endpoint that:
   - Accepts email and password
   - Validates email format and password strength (min 8 chars)
   - Hashes password with bcrypt
   - Returns JWT token on success

2. Create a `/api/auth/login` endpoint that:
   - Accepts email and password
   - Verifies credentials
   - Returns JWT token with user info

3. Create auth middleware that:
   - Validates JWT from Authorization header
   - Attaches user to request context
   - Returns 401 for invalid/expired tokens

Files to reference: `src/api/`, `src/middleware/`

---

## Create dashboard API endpoint

Build a GET `/api/dashboard` endpoint that returns user statistics:

- Total items count
- Items created this week
- Recent activity (last 10 actions)

Include:
- Proper error handling
- Response caching (5 min TTL)
- TypeScript types for response

---

## Fix issue #42: Form validation not working

The signup form doesn't show validation errors properly.

Problem: When a user submits invalid data, errors are logged to console but not displayed.

Solution needed:
1. Update form component to track validation errors in state
2. Display error messages below each invalid field
3. Clear errors when user starts typing

See: `src/components/SignupForm.tsx`

---

<!--
=============================================================================
TEMPLATE - Copy and modify for your tasks
=============================================================================

## [Task Title]

[Clear, specific description of what needs to be done]

Requirements:
- Requirement 1 (be explicit)
- Requirement 2 (include file paths)

Files involved: `path/to/file.ts`

Notes:
- Any additional context
- Edge cases to consider

-->
