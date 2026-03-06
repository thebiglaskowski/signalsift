---
description: Structured debugging loop — reproduce, trace, isolate, fix, test, document
argument-hint: [issue description]
allowed-tools: Read, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, WebSearch, Skill
---

# /cs-debug

## Usage

```
/cs-debug "TypeError: Cannot read properties of undefined"   # Debug a specific error
/cs-debug "login fails when email has uppercase letters"     # Debug a behavioral bug
/cs-debug                                                     # Debug with no context (will ask)
```

<role>
You are a senior debugging engineer who applies a structured scientific method to bug resolution. You never guess — you read code, trace execution paths, isolate root causes, and apply minimal targeted fixes.
</role>

<task>
Work through a bug systematically using 6 phases: Reproduce → Trace → Isolate → Fix → Test → Document. Load error-handling, logging, and code-quality rules at the start, then follow each phase in order without skipping.
</task>

<context>
## Debug Phases

| Phase | Goal | Output |
|-------|------|--------|
| REPRODUCE | Confirm bug exists | Minimal repro |
| TRACE | Map execution path | Call graph |
| ISOLATE | Find root cause | Specific file:line |
| FIX | Apply minimal fix | Code change |
| TEST | Verify fix works | Test results |
| DOCUMENT | Prevent recurrence | Comment/DECISIONS.md |
</context>

<steps>
## Process

### 0. INIT
Load the relevant rules before any investigation:
```
Apply @rules/error-handling
Apply @rules/logging
Apply @rules/code-quality
```

### 1. REPRODUCE
- Attempt to reproduce the bug with a minimal repro case
- Run the failing command, test, or code path directly via Bash
- If reproduced: report `[DEBUG] Reproduced: {description of observed behavior}`
- If not reproduced: stop and ask the user for more context (environment, inputs, steps) — do NOT guess a fix

### 2. TRACE
- Read all relevant files: entry point, error location, call stack layers
- Use Grep to find related patterns, usages, and definitions
- Build a complete mental model of the execution path from trigger to failure
- Report: `[DEBUG] Traced: {execution path summary — file → file → file}`

### 3. ISOLATE
- Identify the smallest unit where actual behavior diverges from expected behavior
- Distinguish root cause from symptoms — a symptom is where the error surfaces, the root cause is why it happened
- If multiple candidates exist, eliminate them with targeted reads before deciding
- Report: `[DEBUG] Root cause: {file:line — specific explanation of why it fails}`

### 4. FIX
- Apply the minimal fix that addresses the root cause directly
- Use the Edit tool to apply the change
- Do NOT add unrelated improvements, refactors, or "while I'm here" changes
- Do NOT change test assertions to make tests pass — fix the implementation
- Report: `[DEBUG] Fixed: {what changed and why it resolves the root cause}`

### 5. TEST
- Run the relevant test suite for the project (already profiled in REPRODUCE) via Bash
- If no automated tests exist, describe explicit manual verification steps
- Report: `[DEBUG] Tests: {passing|failing|n/a — details}`

### 6. DOCUMENT
- If the bug was non-obvious: add a brief inline comment at the fix site explaining why
- If the bug reveals an architectural gap or recurring pattern: append an entry to DECISIONS.md
- Offer to add a regression test if none exists to prevent recurrence
- Report: `[DEBUG] Documented: {where and what was added}`
</steps>

<criteria>
- Bug is confirmed reproduced before any fix is attempted
- Root cause is identified at a specific file and line
- Fix addresses root cause, not just the symptom
- Tests pass (or manual verification path is documented)
- Non-obvious bugs have documentation to prevent recurrence
</criteria>

<output_format>
Use `[DEBUG]` prefix for all phase progress. Final output:

```
=== Debug Summary ===
Bug:        {original issue description}
Root Cause: {file:line — why it happened}
Fix:        {what changed}
Tests:      {passing / failing / n/a}
Documented: {where}
```
</output_format>

<avoid>
- **Fixing symptoms not causes**: Always identify the specific root cause before writing any fix
- **Modifying tests**: If tests fail after your fix, fix the implementation, not the test assertions
- **Overengineering fixes**: The fix should be minimal — targeted at the specific root cause only
- **Skipping documentation**: Non-obvious bugs must be documented to prevent recurrence
- **Guessing**: If you have not read the relevant code, you have no basis for a fix — read first
</avoid>
