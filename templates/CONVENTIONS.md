# Project: [PROJECT_NAME]

> This file provides context to Aider about your project.
> Copy it to your project root and customize it.
> Aider will read this as context for all tasks.

## Overview

Brief description of what this project does.

## Tech Stack

### Frontend (if applicable)
- Framework: React / Vue / Svelte / etc.
- Language: TypeScript / JavaScript
- Styling: Tailwind / CSS Modules / styled-components
- State: Redux / Zustand / Context API

### Backend (if applicable)
- Framework: FastAPI / Express / Django / etc.
- Language: Python / TypeScript / Go
- Database: PostgreSQL / MongoDB / SQLite
- ORM: SQLAlchemy / Prisma / TypeORM

### Infrastructure
- Hosting: Vercel / AWS / GCP / etc.
- CI/CD: GitHub Actions / GitLab CI
- Containerization: Docker (if used)

## Project Structure

```
src/
├── components/     # React components
├── pages/          # Page components / routes
├── api/            # API routes or clients
├── lib/            # Shared utilities
├── types/          # TypeScript types
└── styles/         # Global styles
```

## Commands

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run lint         # Run linter
npm run test         # Run tests
npm run typecheck    # Run TypeScript checks

# Backend (if separate)
uvicorn main:app --reload   # Start FastAPI server
pytest                       # Run Python tests
ruff check .                 # Lint Python code
```

## Coding Standards

### General
- All code must have type annotations (TypeScript strict mode / Python type hints)
- Write tests for new features and bug fixes
- Use conventional commits: feat:, fix:, refactor:, test:, docs:
- Keep functions small and focused (< 50 lines)
- Prefer composition over inheritance

### TypeScript/JavaScript
- Use `const` by default, `let` when needed, never `var`
- Prefer arrow functions for callbacks
- Use async/await over raw promises
- Destructure objects and arrays when appropriate
- Use optional chaining (`?.`) and nullish coalescing (`??`)

### Python
- Follow PEP 8 style guide
- Use dataclasses or Pydantic for data structures
- Type hints on all function signatures
- Use `pathlib.Path` over `os.path`
- Prefer list comprehensions for simple transformations

### Testing
- Test files mirror source structure: `src/foo.ts` → `tests/foo.test.ts`
- Use descriptive test names: `test_user_can_login_with_valid_credentials`
- Mock external services, never make real API calls in tests
- Aim for >80% coverage on critical paths

## Architecture Decisions

### Authentication
[Describe how auth works - JWT, sessions, OAuth providers, etc.]

### API Design
[REST vs GraphQL, versioning strategy, error handling conventions]

### State Management
[How state is managed, where data lives, caching strategy]

## Don't Touch

These files/directories should not be modified by Aider:

- `.env` / `.env.*` - Environment variables (secrets)
- `migrations/` - Database migrations (create manually)
- `node_modules/` / `venv/` - Dependencies
- `.git/` - Git internals
- `*.lock` files - Dependency lock files
- `dist/` / `build/` - Build outputs

## Known Issues / Technical Debt

- [ ] Need to refactor auth module (too complex)
- [ ] Some API endpoints lack proper validation
- [ ] Test coverage low in `src/legacy/`

## External Services

| Service | Purpose | Docs |
|---------|---------|------|
| Stripe | Payments | https://stripe.com/docs |
| SendGrid | Email | https://docs.sendgrid.com |
| Redis | Caching | https://redis.io/docs |

## Common Patterns

### Error Handling (TypeScript)
```typescript
// Use Result type for operations that can fail
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };

// Throw only for truly exceptional cases
// Return Result for expected failure modes
```

### Error Handling (Python)
```python
# Use custom exceptions with clear names
class UserNotFoundError(Exception):
    pass

# Return Optional for queries that might not find results
def get_user(id: str) -> User | None:
    ...
```

### API Responses
```typescript
// Consistent response format
interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: {
        code: string;
        message: string;
    };
}
```

## Notes for AI

- When adding new features, check for similar existing implementations first
- Prefer modifying existing files over creating new ones
- Always run `npm run typecheck` and `npm run test` after changes
- If you're unsure about a pattern, follow what's already in the codebase
- Don't add comments that just restate what the code does
- Don't add try/catch blocks unless there's meaningful error handling
