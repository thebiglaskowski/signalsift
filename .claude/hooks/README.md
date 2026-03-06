# Claude Sentient Hooks

This directory contains hook scripts that integrate with Claude Code's hook system.

## Hook Types

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start.cjs` | SessionStart | Initialize session, detect profile |
| `session-end.cjs` | SessionEnd | Archive session, cleanup |
| `context-injector.cjs` | UserPromptSubmit | Detect topics, inject context |
| `bash-validator.cjs` | PreToolUse (Bash) | Block dangerous commands |
| `file-validator.cjs` | PreToolUse (Write/Edit) | Validate file paths |
| `post-edit.cjs` | PostToolUse (Write/Edit) | Track changes, suggest lint |
| `agent-tracker.cjs` | SubagentStart | Track agent spawning |
| `agent-synthesizer.cjs` | SubagentStop | Synthesize agent results |
| `pre-compact.cjs` | PreCompact | Backup state before compaction |
| `dod-verifier.cjs` | Stop | Verify Definition of Done |
| `teammate-idle.cjs` | TeammateIdle | Quality check before teammate goes idle |
| `task-completed.cjs` | TaskCompleted | Validate deliverables, file ownership |

## State Files

Hooks read/write to `.claude/state/`:

| File | Purpose |
|------|---------|
| `session_start.json` | Current session metadata |
| `file_changes.json` | Files modified this session |
| `active_agents.json` | Currently running subagents |
| `agent_history.json` | Completed subagent history |
| `prompts.json` | Recent prompt metadata |
| `last_verification.json` | Last DoD verification |
| `team-state.json` | Agent Teams: teammate tracking, file ownership |

## Security

### Bash Validator Blocked Patterns

- `rm -rf /` or `rm -rf ~` - Recursive delete from root/home
- `> /dev/sd*` - Direct disk writes
- `mkfs` - Filesystem creation
- `chmod -R 777 /` - Dangerous permission changes
- Fork bombs and reverse shells

### File Validator Protected Paths

- System directories (`/etc`, `/usr`, `C:\Windows`)
- SSH keys (`.ssh/`)
- Credentials (`.env.production`, `secrets.*`)
- Git internals (`.git/objects`)

## Customization

To add custom validation, edit the respective hook file:

```javascript
// In bash-validator.cjs, add to DANGEROUS_PATTERNS:
{ pattern: /your-pattern/, reason: 'Your reason' }

// In file-validator.cjs, add to PROTECTED_PATHS:
/your-path-pattern/
```

## Hook Input/Output

Hooks receive input via `HOOK_INPUT` environment variable (JSON):

```javascript
const input = JSON.parse(process.env.HOOK_INPUT || '{}');
// input.tool_input - the tool's parameters
// input.tool_name - which tool triggered
```

Hooks output JSON to stdout:

```javascript
// Block an operation
console.log(JSON.stringify({ decision: 'block', reason: 'Why' }));

// Allow with warnings
console.log(JSON.stringify({ decision: 'allow', warnings: ['Warning'] }));

// Inject context
console.log(JSON.stringify({ continue: true, context: { key: 'value' } }));
```

## Debugging

Enable verbose logging:

```bash
# All hook activity is logged to:
cat .claude/session.log

# Session state:
cat .claude/state/session_start.json

# File changes this session:
cat .claude/state/file_changes.json
```

## Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "node .claude/hooks/bash-validator.cjs",
          "timeout": 5000
        }]
      }
    ]
  }
}
```

See `settings.json` for the full configuration.
