# Agents — Claude Sentient

> Context for working on agent definition files.

## Dual Agent System

Agents exist in two formats that serve complementary purposes:

| Format | Location | Purpose |
|--------|----------|---------|
| **Native agents** | `.claude/agents/*.md` | Claude Code-native agents with frontmatter (model, tools, permissions, skills) — directly invocable via `--agent` flag or `Task(subagent_type="agent-name")` |
| **YAML configs** | `agents/*.yaml` | Schema-validated configuration — tested by `test-agents.js`, used by `/cs-team` for expertise matching and team design |

The YAML files are the source of truth for agent metadata (expertise, role, file scopes). The native `.md` agents are the runtime format that Claude Code uses directly.

---

## Native Agent Format (.claude/agents/*.md)

```markdown
---
name: backend
description: "Backend specialist for API design and database operations"
model: sonnet
permissionMode: acceptEdits
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
skills:
  - quality-gates
---

You are a backend specialist. Your focus areas include:
[spawn_prompt content from YAML]

## Rules
Apply rules from: api-design, error-handling, database

## Quality Gates
Run before completing any task: lint, test, build

## File Scope
Focus on files matching: controllers, routes, services, models
```

### Frontmatter Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier (kebab-case) |
| `description` | string | When to invoke this agent |
| `model` | enum | `haiku`, `sonnet`, `opus`, or `inherit` |
| `permissionMode` | enum | `default`, `acceptEdits`, `plan`, `dontAsk` |
| `tools` | array | Allowlist of permitted tools |
| `skills` | array | Skills preloaded at startup |
| `maxTurns` | number | Maximum agentic iterations (optional) |
| `memory` | enum | `user`, `project`, `local` (optional) |
| `isolation` | string | `"worktree"` for git worktree isolation (optional) |

---

## YAML Config Format (agents/*.yaml)

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier (kebab-case, matches filename) |
| `description` | string | One-line description (10+ chars) |
| `version` | string | Semver version |
| `role` | enum | `implementer`, `reviewer`, `researcher`, `tester`, or `architect` |
| `expertise` | array | Areas of expertise (3+ items) |
| `spawn_prompt` | string | Detailed initialization prompt (50+ chars) |
| `quality_gates` | array | Gates to run: `lint`, `test`, `build` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `rules_to_load` | array | Rule files from `rules/` to inject into context |
| `file_scope_hints` | array | Glob patterns for files this agent works with |

---

## How Agents Are Used

1. `/cs-team` reads `agents/*.yaml` for expertise matching and team design
2. Native `.claude/agents/*.md` agents are spawned via `Task(subagent_type="agent-name")`
3. Agent `skills` are preloaded at startup (e.g., quality-gates skill)
4. Agent `quality_gates` are enforced via hooks (TeammateIdle, TaskCompleted)
5. Falls back to generic role prompts if no matching agent exists

---

## Adding a Custom Agent

1. Create `agents/{name}.yaml` with all required YAML fields
2. Create `.claude/agents/{name}.md` with native frontmatter
3. Ensure `rules_to_load` references exist in `rules/` directory
4. Use specific `file_scope_hints` to avoid overlap with other agents
5. Run `node agents/__tests__/test-agents.js` to validate YAML
6. The agent becomes available to `/cs-team` and `Task(subagent_type)` automatically

---

## Schema

YAML agent definitions are validated against `schemas/agent.schema.json`.
