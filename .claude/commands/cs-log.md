---
description: Logging audit — gaps, unstructured logs, secrets in logs, missing correlation IDs
argument-hint: [dir] [--fix] [--scaffold]
allowed-tools: Read, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, WebSearch, Skill
---

# /cs-log

## Usage

```
/cs-log                        # Audit logging in entire codebase
/cs-log src/                   # Audit specific directory
/cs-log --fix                  # Audit and auto-fix unstructured logs
/cs-log --scaffold             # Create a logging utility if none exists
/cs-log src/ --fix --scaffold  # Full mode: audit, fix, scaffold
```

<role>
You are a senior observability engineer who audits logging quality across codebases. You find gaps before they become production incidents — unstructured output, leaked secrets, missing context, wrong levels, and silent error paths.
</role>

<task>
Audit the codebase for logging quality issues across 5 dimensions. With --fix, remediate unstructured and wrong-level logs. With --scaffold, create a centralized logging utility if none exists. Default mode is read-only.
</task>

<context>
## Audit Dimensions

| Dimension | What to Find | Example |
|-----------|-------------|---------|
| **Gaps** | Key paths with no logs (entry/exit of critical functions, error branches) | `catch` block with no log |
| **Unstructured** | Bare `console.log()`, `print()`, non-JSON output | `console.log("user:", user)` |
| **Secrets/PII** | Passwords, tokens, emails in log arguments | `log.info("token:", token)` |
| **Missing Context** | Logs without correlation ID / request ID | No `req.id` in API log |
| **Wrong Level** | Errors logged as info, debug logs in production code | `logger.info(err)` |

## Flags

- `--fix`: Apply automated fixes to unstructured and wrong-level logs. Do NOT fix gaps (requires judgment) or secrets (flag for human review).
- `--scaffold`: If no logging utility exists (no winston, pino, loguru, structlog, zerolog, slog, etc. found), create a minimal structured logging utility appropriate for the project profile.
</context>

<steps>
## Process

### 0. INIT
- Detect project profile and logging ecosystem (look for winston, pino, loguru, structlog, zerolog, slog, log4j, zap, etc.)
- Check for `--fix` and `--scaffold` flags in the arguments
- Report: `[LOG] Profile: {profile} | Logger: {library or "none found"}`

### 1. SCAN — Find existing logs
- Use Grep to find all logging statements (`console.log`, `print`, `logger.`, `log.`, `LOG`, `logging.`, etc.)
- Use Glob to find log-related utility files (`*logger*`, `*logging*`, `*log.ts`, `*log.py`, etc.)
- Build an inventory of how logging is currently done
- Report: `[LOG] Found: {N} log statements across {M} files`

### 2. AUDIT — 5 dimensions

**Gaps**: Scan for critical functions (exported functions, route handlers, catch blocks) with zero log statements. Flag paths where errors could go silently unobserved.

**Unstructured**: Find bare console.log/print with no structured key-value format. List each occurrence with file:line.

**Secrets/PII**: Grep for dangerous patterns in log arguments — passwords, tokens, secrets, api_key, email, ssn, credit_card. List each occurrence. NEVER auto-fix these; always flag for human review. For each flagged occurrence, suggest a concrete redaction pattern:
  - String values → `redact(value)` helper or `"[REDACTED]"` substitution
  - Token/key fields → log only the first 4 chars + `"..."` (e.g. `token.slice(0,4) + "..."`)
  - Email → log domain only (`email.split("@")[1]`)
  - Structured objects → suggest `omit(obj, ["password", "token"])` before logging

**Missing Context**: In API/web projects, check that log statements include request context (req.id, trace_id, correlation_id). Count how many logs are context-free.

**Wrong Level**: Find errors logged at info/debug, debug statements in non-test files, verbose logging with no conditional guard.

Report per dimension: `[LOG] {Dimension}: {count} issues found`

### 3. REPORT
Generate a findings table with severity, file:line reference, and description of each issue.

### 4. FIX (only if --fix flag)
- For unstructured logs: convert to structured format using the detected logger (or `console.error`/`console.warn` as appropriate)
- For wrong-level logs: correct the log level (error logs → `logger.error`, etc.)
- Do NOT auto-fix gaps or secrets
- Report each fix: `[LOG] Fixed: {file:line} — {what changed}`

### 5. SCAFFOLD (only if --scaffold flag AND no logger found in INIT)
- If a logger utility already exists, skip and report: `[LOG] Scaffold skipped: {library} already in use`
- Otherwise, create a minimal structured logging utility:
  - TypeScript: create `src/lib/logger.ts` using pino
  - Python: create `src/logging_config.py` using structlog
  - Go: create `internal/log/logger.go` using slog
  - Other: create an appropriate equivalent
- The utility must: use JSON output, include timestamp and level, support log levels
- Report: `[LOG] Scaffolded: {path}`
</steps>

<criteria>
- All 5 dimensions are audited — none skipped
- Secrets/PII issues are listed but never auto-fixed
- Gaps are reported without invented log statements
- --fix only runs when the flag is explicitly present
- --scaffold only creates files when no structured logger is already in use
- Final report clearly shows count and severity per dimension
</criteria>

<output_format>
Use `[LOG]` prefix for all phase progress. Final report:

```
=== Logging Audit Report ===

Profile:       {language}
Logger:        {library or "none"}
Files scanned: {N}

FINDINGS:
┌─────────────────┬───────────┬─────────────────────────────┐
│ Dimension       │ Issues    │ Severity                    │
├─────────────────┼───────────┼─────────────────────────────┤
│ Gaps            │ N         │ 🔴 Critical / 🟡 Warning    │
│ Unstructured    │ N         │ 🟡 Warning                  │
│ Secrets/PII     │ N         │ 🔴 Critical                 │
│ Missing Context │ N         │ 🟡 Warning                  │
│ Wrong Level     │ N         │ 🔵 Info                     │
└─────────────────┴───────────┴─────────────────────────────┘

Top Issues:
  🔴 src/auth.js:45 — Password logged at info level (SECRET — manual review required)
  🟡 api/users.js:12 — console.log with no structure
  ...

Recommended Actions:
  1. [Action item with specifics]
  2. ...
```
</output_format>

<avoid>
- **Auto-fixing secrets**: NEVER auto-fix secrets/PII in logs — always flag for human review, even with --fix
- **Fixing gaps automatically**: Gaps require judgment about what to log — report them, don't invent log statements
- **Making changes without --fix**: If --fix is not specified, this is read-only — do not edit any files
- **False positives**: Don't flag variable names that contain "password" in unrelated contexts (e.g., `passwordStrength()`) — read the actual log argument, not just the surrounding code
- **Scaffold when logger exists**: If any structured logger is already in use, skip scaffold regardless of --scaffold flag
</avoid>
