# Overnight Tasks - [DATE]

> Instructions for creating task files:
> - Each ## heading becomes a task
> - Be specific and provide context
> - Include acceptance criteria when helpful
> - Mention related files if known
> - Tasks run sequentially, so order them logically

---

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

4. Add tests for all auth endpoints

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

## Add rate limiting to API

Implement rate limiting to prevent abuse:

- Limit: 100 requests per minute per IP
- Return 429 Too Many Requests when exceeded
- Add X-RateLimit-* headers to responses
- Exempt authenticated admin users

Use redis if available, otherwise in-memory store.

---

## Improve test coverage for user service

The user service has low test coverage. Add tests for:

- `createUser()` - success and duplicate email cases
- `updateUser()` - valid update and not found cases
- `deleteUser()` - success and cascade behavior
- `getUserById()` - found and not found cases

Target: >90% coverage for `src/services/userService.ts`

---

## Refactor database queries to use transactions

Several operations need to be atomic but aren't using transactions.

Update these functions to use database transactions:
- `createOrder()` - should atomically create order + line items
- `transferFunds()` - should atomically debit and credit accounts
- `bulkUpdateStatus()` - should update all or none

Add rollback on any failure.

---

<!--
Template for adding more tasks:

## [Task Title]

[Clear description of what needs to be done]

Requirements:
- Requirement 1
- Requirement 2

Files involved: `path/to/file.ts`

Notes:
- Any additional context
- Edge cases to consider

-->
