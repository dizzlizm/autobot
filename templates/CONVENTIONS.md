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

### Mobile (Expo/React Native)
- Framework: Expo SDK [version]
- Router: Expo Router / React Navigation
- UI: React Native Paper / NativeWind / etc.
- Storage: AsyncStorage / Expo SecureStore

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
# Development (Web)
npm run dev          # Start development server
npm run build        # Build for production
npm run lint         # Run linter
npm run test         # Run tests
npm run typecheck    # Run TypeScript checks

# Development (Expo/Mobile)
npx expo start       # Start dev server (scan QR with Expo Go)
npx expo start --ios # Start iOS simulator
npx expo start --android # Start Android emulator
npx expo doctor      # Check for issues
npx expo export      # Build web bundle (validation)

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

## Mobile/Expo Patterns

### Navigation (Expo Router)
```typescript
// File-based routing in app/ directory
// app/(tabs)/index.tsx -> "/"
// app/(tabs)/profile.tsx -> "/profile"
// app/settings/[id].tsx -> "/settings/:id"

// Navigation
import { router } from 'expo-router';
router.push('/profile');
router.replace('/login');
router.back();
```

### Native Components
```typescript
// Use React Native components, not web HTML
import { View, Text, Pressable, ScrollView } from 'react-native';

// NOT <div>, <span>, <button>, <p>
// Use View for containers, Text for all text, Pressable for buttons
```

### Platform-Specific Code
```typescript
import { Platform } from 'react-native';

const styles = {
  shadow: Platform.select({
    ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 } },
    android: { elevation: 4 },
  }),
};
```

### Safe Areas
```typescript
import { SafeAreaView } from 'react-native-safe-area-context';

// Always wrap screens in SafeAreaView for notches/status bars
export default function Screen() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      {/* content */}
    </SafeAreaView>
  );
}
```

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

### Critical Rules
- **ONE TASK AT A TIME**: Focus only on the current task
- **MINIMAL CHANGES**: Change only what is necessary
- **FOLLOW PATTERNS**: Copy existing code patterns exactly
- **NO EXTRAS**: Do not add comments, docstrings, or type hints unless asked

### Step-by-Step Approach
1. Read the existing file first
2. Find similar code to use as reference
3. Make the smallest change that works
4. Verify the change matches existing style

### Do NOT
- Add comments that explain obvious code
- Refactor code you weren't asked to change
- Add error handling unless specifically needed
- Create new files when you can modify existing ones
- Add type annotations to files that don't have them
- Change formatting or whitespace
