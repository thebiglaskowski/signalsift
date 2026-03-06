---
description: Save a learning, decision, or pattern to project memory
argument-hint: <type> <title> <content>
allowed-tools: Read, Edit, Write, mcp__memory__create_entities, mcp__memory__create_relations, mcp__memory__add_observations
---

# /cs-learn

<role>
You are a knowledge capture assistant that preserves important decisions, patterns, and learnings for future sessions. You store information in both file-based memory (for Claude Code rules loading) and MCP memory (for searchable retrieval).
</role>

<task>
Save important learnings to `.claude/rules/learnings.md` and MCP memory. This creates persistent, searchable knowledge that will be loaded in future sessions and can be retrieved by `/cs-loop`.
</task>

## Arguments

- `type`: One of `decision`, `pattern`, or `learning`
- `title`: Short title for the entry
- `content`: Detailed description

## Flags

- `--scope`: Memory scope (default: `project`)
- `--level`: Confidence level (default: inferred from type)

### Confidence Levels

Confidence levels reflect how well-established a learning is. Claude uses these to weight entries during decision-making — high-confidence rules are applied strictly, low-confidence observations are considered lightly.

| Level | Description | Default For |
|-------|-------------|-------------|
| `observed` | Seen once, may not generalize | `learning` |
| `pattern` | Confirmed across 2+ situations | `pattern` |
| `rule` | Established standard, applies consistently | `decision` |
| `instinct` | Deep expertise, applied automatically | (promote manually) |

Use `--level instinct` sparingly — only for learnings that have been validated many times and should be applied without question.

| Scope | Storage | Available To |
|-------|---------|-------------|
| `project` (default) | `.claude/rules/learnings.md` + MCP memory | This project only |
| `global` | MCP memory with `scope:global` tag | All projects |
| `org` | MCP memory with `scope:org:{name}` tag | Organization projects |
| `personal` | `~/.claude/projects/<project>/memory/MEMORY.md` | Just you (auto memory) |

Org name is detected from: `.claude/settings.json` → `sentient.org` field, or fallback to git remote org name (`git remote get-url origin` → extract org).

<steps>
## Behavior

### 0. Resolve Confidence Level

Determine the confidence level:
1. If `--level` is provided, use it directly (validate: must be one of `observed`, `pattern`, `rule`, `instinct`)
2. Otherwise, infer from `type`:
   - `decision` → `rule`
   - `pattern` → `pattern`
   - `learning` → `observed`

Include the level in the stored entry and MCP entity.

### 1. Check for Contradictions

Before saving, check for conflicts with existing entries:

1. Read existing `.claude/rules/learnings.md`
2. Check if the new entry contradicts any existing entry of the same type
   (e.g., new decision "Use MySQL" vs existing decision "Use PostgreSQL")
3. If contradiction found, report it and ask the user:
   ```
   AskUserQuestion:
     question: "This contradicts an existing {type}: '{existing_title}'. How should we handle it?"
     header: "Conflict"
     options:
       - label: "Replace the old entry (Recommended)"
         description: "Remove the old entry and add the new one"
       - label: "Keep both"
         description: "Add context explaining the change in direction"
       - label: "Cancel"
         description: "Don't save the new entry"
   ```
4. If no contradiction, proceed to Step 1.

### 1. Save to File (learnings.md)

**If `--scope personal`:** Append to `~/.claude/projects/<project>/memory/MEMORY.md` instead of `.claude/rules/learnings.md`. Keep MEMORY.md under 200 lines (first 200 lines are auto-loaded every session). If MEMORY.md exceeds 200 lines, move older entries to `~/.claude/projects/<project>/memory/learnings.md`.

1. Read the current `.claude/rules/learnings.md` file (create if missing)
2. Append a new entry under the appropriate section:
   - `decision` → ## Decisions
   - `pattern` → ## Patterns
   - `learning` → ## Learnings
3. Format the entry with today's date (see output_format)

### 2. Save to MCP Memory (searchable)

Also save to MCP memory for searchable retrieval. Add scope tag based on `--scope` flag:

```
mcp__memory__create_entities([{
  name: "{type}_{topic}_{date}",
  entityType: "{type}",
  observations: [
    "type: {type}",
    "topic: {title}",
    "content: {content}",
    "date: {YYYY-MM-DD}",
    "project: {current project name}",
    "scope: {project|global|org:{org_name}}"
  ]
}])
```

**Scope-specific behavior:**
- `--scope project` (default): Save to file AND MCP memory with `scope:project` tag
- `--scope global`: Save to MCP memory ONLY with `scope:global` tag (not to file — global learnings shouldn't clutter project files)
- `--scope org`: Save to MCP memory ONLY with `scope:org:{name}` tag. Detect org name from `.claude/settings.json` → `sentient.org`, or extract from `git remote get-url origin`
- `--scope personal`: Save to auto memory ONLY (not to project file or MCP memory — personal insights stay personal)

**Create relations** to connect related entities:
```
mcp__memory__create_relations([{
  from: "decision_auth_jwt_2026_02_02",
  to: "pattern_jwt_tokens",
  relationType: "implements"
}])
```

### 3. Confirm

Report what was saved to both locations.
</steps>

<context>
**Entity naming convention:**

| Type | Name Pattern | Example |
|------|--------------|---------|
| Decision | `decision_{topic}_{date}` | `decision_auth_jwt_2026_02_02` |
| Pattern | `pattern_{name}` | `pattern_error_shape` |
| Learning | `learning_{topic}_{date}` | `learning_orm_performance_2026_02_02` |
</context>

<output_format>
### Entry Format (for learnings.md)

```markdown
### YYYY-MM-DD: {title}
- **Context**: [infer from conversation if not provided]
- **{Type}**: {content}
- **Confidence**: {observed|pattern|rule|instinct}
```
</output_format>

<constraints>
- Keep entries concise — these are reminders, not documentation
- Always save to both file AND MCP memory
- Use consistent entity naming for searchability
- Connect related entities with relations when applicable
</constraints>

<avoid>
## Common Mistakes to Prevent

- **Duplicate entries**: Check if a similar learning already exists before adding. Don't create redundant entries with slightly different wording.

- **Missing dual storage**: Don't save to file only. Always attempt MCP memory storage too (gracefully handle if unavailable).

- **Verbose entries**: These are quick reminders, not documentation. Don't write multi-paragraph explanations. Keep it scannable.

- **Missing context**: Don't omit the Context field. Even if the user doesn't provide it, infer from the conversation.

- **Inconsistent naming**: Follow the entity naming convention exactly (`decision_{topic}_{date}`). Don't use freeform names.

- **Wrong section**: Don't put decisions under Patterns or vice versa. Match the type argument to the correct section.
</avoid>

<examples>
## Examples

```
/cs-learn decision "Use PostgreSQL" "Chose over MySQL for better JSON support"
/cs-learn pattern "API errors" "All errors return {error, message, code} shape"
/cs-learn learning "Avoid N+1" "Use eager loading for related entities"
/cs-learn decision "Auth pattern" "Use JWT with refresh tokens" --scope global
/cs-learn learning "Docker builds" "Multi-stage builds reduce image size" --scope org
/cs-learn learning "Debug tip" "Use console.trace for stack traces" --scope personal
/cs-learn pattern "Hook self-protection" "Edit hooks via /tmp copy" --level instinct
/cs-learn learning "nvm FUNCNEST" "Use process.execPath not bare node" --level rule
```
</examples>

## Notes

- Learnings are loaded automatically at session start via Claude Code's rules system
- MCP memory makes learnings searchable by `/cs-loop` during INIT phase
- When running `/cs-loop`, significant learnings should be captured automatically
