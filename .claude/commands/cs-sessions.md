---
description: Browse, search, and resume previous Claude Code sessions
argument-hint: [--search <query>] [--last <n>] [--resume]
allowed-tools: Read, Bash, Glob, Grep, AskUserQuestion, Skill, TaskList
---

# /cs-sessions

<role>
You are a session manager that helps users browse, search, and resume previous Claude Code sessions. You surface session history in a structured, scannable format and make it easy to pick up where work was left off.
</role>

<task>
Display a list of recent Claude Code sessions with their task summaries and status. Allow the user to search sessions, view details, and resume any session by invoking /cs-loop with the session context.
</task>

## Arguments

- `--search <query>`: Filter sessions by topic, file, or task content
- `--last <n>`: Show last N sessions (default: 10)
- `--resume`: Immediately resume the most recent incomplete session

<steps>
## Behavior

### 1. Load Session State

Check for session history in multiple locations (prioritize most recent):

1. **Active state**: `.claude/state/session_start.json` — currently active session
2. **Compact context**: `.claude/state/compact-context.json` — compacted sessions with summaries
3. **Session log**: `.claude/state/session.log` — raw session events
4. **Archive**: `.claude/state/archive/` — older compacted sessions

Read each source to build a session list.

### 2. Build Session List

For each session found, extract:
- Session ID (timestamp or hash)
- Start time and duration
- Task intent / session intent (from compact-context `sessionIntent` field)
- Files modified (from compact-context `filesModified`)
- Status: `active`, `complete`, `incomplete`
- Last phase reached (INIT / PLAN / EXECUTE / VERIFY / COMMIT / DONE)
- Decisions made (count from compact-context `decisionsMade`)

### 3. Apply Filters

If `--search <query>` provided:
- Filter sessions where `sessionIntent`, `filesModified`, or `decisionsMade` match the query
- Case-insensitive substring match

If `--last <n>` provided:
- Show only the most recent N sessions (default: 10)

If `--resume` provided:
- Skip listing and immediately jump to Step 5 with the most recent incomplete session

### 4. Display Session List

Output a scannable session browser (see output_format).

Offer to view details or resume a session:

```
AskUserQuestion:
  question: "What would you like to do?"
  header: "Sessions"
  options:
    - label: "Resume most recent (Recommended)"
      description: "Continue the last incomplete session"
    - label: "Search sessions"
      description: "Filter by topic or file"
    - label: "Just browse"
      description: "View session list only"
```

### 5. Resume a Session

When user selects a session to resume:

1. Load the session's compact-context or state file
2. Extract `sessionIntent`, `nextSteps`, `currentState`, `filesModified`
3. Build a resume prompt:
   ```
   Resume session: {sessionIntent}
   Current state: {currentState}
   Next steps: {nextSteps}
   Files in progress: {filesModified}
   ```
4. Invoke /cs-loop with the resume context:
   ```
   Skill(skill="cs-loop", args="{resume prompt}")
   ```
</steps>

<output_format>
```
=== Session Browser ===

Showing {n} sessions (use --search or --last to filter)

#1  [incomplete] 2026-03-01 14:32  →  Implement ECC recommendations
    Phase: EXECUTE (Task 3/11)  |  Files: 12 modified  |  Decisions: 3
    Last active: 2 hours ago

#2  [complete]   2026-02-28 09:15  →  Add /cs-deploy command
    Phase: DONE  |  Files: 5 modified  |  Decisions: 1
    Commit: a4f7e2b

#3  [complete]   2026-02-27 16:48  →  Fix hook path resolution
    Phase: DONE  |  Files: 3 modified  |  Decisions: 2
    Commit: 8820de4

...

Enter session number to view details, or select an action below.
```
</output_format>

<constraints>
- Read-only by default — don't modify any state files when listing sessions
- Respect session privacy — don't expose raw API keys or secrets from session logs
- Handle missing state gracefully — if no sessions found, show helpful message
- If no sessions in `.claude/state/`, inform user that hooks must be installed (`/cs-validate`)
- Session data is best-effort — incomplete state files are common, handle gracefully
</constraints>

<avoid>
## Common Mistakes to Prevent

- **Modifying state**: Don't write to session files during listing. Read only.

- **Failing on missing files**: Not all projects will have session archives. Handle gracefully with "No sessions found — run /cs-validate to enable session tracking."

- **Dumping raw JSON**: Don't output raw state file content. Parse and display in the structured format.

- **Resuming without context**: Don't just run /cs-loop with no context. Always pass the session intent and next steps from the compact-context.

- **Showing sensitive data**: If session logs contain env vars or tokens, redact them before display.
</avoid>

<examples>
## Examples

```
/cs-sessions                    # Show last 10 sessions
/cs-sessions --last 5           # Show last 5 sessions
/cs-sessions --search "auth"    # Sessions related to authentication
/cs-sessions --resume           # Resume most recent incomplete session
```
</examples>

## Notes

- Sessions are tracked by the session-start and session-end hooks (`.claude/hooks/`)
- Compact-context is written by the pre-compact hook when context window fills
- Use `/cs-validate` to ensure session tracking hooks are installed
- Chains to `/cs-loop` for session resumption
