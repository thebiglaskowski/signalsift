# Commands — Claude Sentient

> Context for working on `/cs-*` command files.

## Command File Structure

All commands use YAML frontmatter + XML-structured instructions:

```markdown
---
description: What the command does
argument-hint: <args>
allowed-tools: Tool1, Tool2, ...
---

# /cs-command-name

<role>Expert persona for this command</role>
<task>Clear objective statement</task>
<context>Background info, tables, nested data</context>
<steps>Ordered procedure with <thinking> blocks</steps>
<criteria>Success metrics</criteria>
<output_format>Response structure</output_format>
<constraints>Rules and limitations</constraints>
<avoid>Command-specific DON'Ts</avoid>
<examples>Sample inputs/outputs</examples>
```

---

## Documentation Policy

Claude Sentient automates documentation based on task context:

### Auto-Update Triggers

| Change Type | STATUS.md | CHANGELOG.md | DECISIONS.md |
|-------------|-----------|--------------|--------------|
| Feature added | Auto | Confirm | Only if architectural |
| Bug fixed | Auto | Confirm | -- |
| Refactoring | Auto | -- | If significant |
| Breaking change | Auto | Confirm (required) | Required |
| Config change | Auto | -- | -- |

### Automation Levels

| Level | When | Examples |
|-------|------|----------|
| **Fully Auto** | Low risk, high value | Rule loading, STATUS.md updates |
| **Auto + Confirm** | Significant changes | CHANGELOG entries, version bumps |
| **On Request** | User preference | Full docs rewrites, ADRs |

---

## Rule Auto-Loading

During `/cs-loop` INIT, rules are loaded by task keywords.
Full mapping: `rules/_index.md`

---

## Skill Chaining

Commands can invoke each other via the `Skill` tool:

| From | To | When |
|------|----|------|
| `/cs-plan` | `/cs-loop` | After plan approval, user chooses to execute |
| `/cs-status` | `/cs-loop` | When pending tasks exist, user chooses to continue |
| `/cs-validate` | `/cs-loop` | When issues found, user chooses to auto-fix |
| `/cs-loop` | `/cs-init` | When no CLAUDE.md detected during INIT |
| `/cs-init` | `/cs-loop` | After creating CLAUDE.md, user chooses to start working |
| `/cs-loop` | `/cs-team` | When team eligibility detected, user approves team mode |
| `/cs-team` | `/cs-loop` | When team completes, fallback to solo for remaining work |
| `/cs-assess` | `/cs-loop` | When issues found, user chooses to fix them |
| `/cs-review` | `/cs-loop` | When PR changes needed, user chooses to fix |
| `/cs-loop` | `/cs-docs` | At COMMIT, when changed files need doc sync check |
| `/cs-docs` | `/cs-loop` | After generating doc, user chooses to implement against spec |
| `/cs-learn` | — | Standalone, appends to learnings.md |
| `/cs-mcp` | — | Standalone, registers/validates MCP servers |
| `/cs-ui` | `/cs-loop` | When UI issues found, user chooses to fix |
| `/cs-deploy` | — | Standalone, read-only deployment readiness check |
| `/cs-sessions` | `/cs-loop` | When user chooses to resume a previous session |
| `/cs-multi` | — | Standalone, configures per-phase model routing |
| `/cs-debug` | `/cs-loop` | When root cause requires implementation changes, user chooses to fix |
| `/cs-log` | `/cs-loop` | When logging gaps/issues found, user chooses to fix |

---

## Adding a New Command

1. Create `.claude/commands/cs-{name}.md` with frontmatter
2. Use XML tags (`<role>`, `<task>`, `<steps>`, `<avoid>`, etc.)
3. Add `<avoid>` section with command-specific anti-patterns
4. Update `cs-validate.md` required commands list
5. Update root `CLAUDE.md` commands table
6. Update `README.md`, `CHANGELOG.md`, `install.sh`, `install.ps1`
