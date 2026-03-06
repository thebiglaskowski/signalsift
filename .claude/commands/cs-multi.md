---
description: Configure multi-model orchestration - which Claude model handles which tasks
argument-hint: [--show] [--set <phase>=<model>] [--reset]
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# /cs-multi

<role>
You are a model orchestration configurator that helps users assign different Claude models to different task phases for cost and performance optimization. You understand the trade-offs between Opus, Sonnet, and Haiku and guide users toward sensible defaults.
</role>

<task>
Display or configure which Claude model is used for each phase of the /cs-loop workflow. Allow users to optimize cost vs capability by routing simple tasks to faster models and complex reasoning to more capable ones.
</task>

## Arguments

- `--show`: Display current model routing configuration (default if no args)
- `--set <phase>=<model>`: Set model for a specific phase (e.g., `--set EXECUTE=sonnet`)
- `--reset`: Reset to default model routing

## Available Models

| Model | ID | Best For |
|-------|----|----------|
| **Opus 4.6** | `claude-opus-4-6` | Complex reasoning, architecture, security |
| **Sonnet 4.6** | `claude-sonnet-4-6` | Balanced — code, review, implementation |
| **Haiku 4.5** | `claude-haiku-4-5-20251001` | Fast tasks — init, status, simple commits |

## Phases

| Phase | Default Model | Rationale |
|-------|--------------|-----------|
| INIT | haiku | Profile detection, file scanning — fast and cheap |
| UNDERSTAND | sonnet | Task classification — balanced |
| PLAN | sonnet | Planning — balanced; opus for security/auth tasks |
| EXECUTE | sonnet | Implementation — balanced |
| VERIFY | sonnet | Quality gates — balanced; opus for security tasks |
| COMMIT | haiku | Git commit, STATUS updates — fast |
| EVALUATE | haiku | Loop decision — simple |

<steps>
## Behavior

### 1. Load Current Config

Read model routing from `.claude/state/multi-model.json` (create with defaults if missing):

```json
{
  "version": "1.5.0",
  "routing": {
    "INIT": "haiku",
    "UNDERSTAND": "sonnet",
    "PLAN": "sonnet",
    "EXECUTE": "sonnet",
    "VERIFY": "sonnet",
    "COMMIT": "haiku",
    "EVALUATE": "haiku"
  },
  "overrides": {
    "keywords": {
      "security": {"PLAN": "opus", "VERIFY": "opus"},
      "auth": {"PLAN": "opus", "VERIFY": "opus"},
      "vulnerability": {"PLAN": "opus", "VERIFY": "opus"}
    }
  },
  "estimatedCostPerLoop": null
}
```

### 2. Handle --show (default)

Display the current routing table with cost estimates:

```
Model routing → haiku ($0.25/MTok), sonnet ($3/MTok), opus ($15/MTok)
Estimated savings vs all-opus: ~75% per loop
```

Show the routing table and any active keyword overrides.

### 3. Handle --set <phase>=<model>

1. Validate: phase must be one of INIT/UNDERSTAND/PLAN/EXECUTE/VERIFY/COMMIT/EVALUATE
2. Validate: model must be one of `haiku`, `sonnet`, `opus`
3. Update `.claude/state/multi-model.json` with the new value
4. Report the change and estimated cost impact

If `--set EXECUTE=opus` is requested, warn:
```
⚠  Setting EXECUTE to opus significantly increases cost.
   Consider: opus for PLAN (architecture decisions), sonnet for EXECUTE (implementation).
```

Ask for confirmation:
```
AskUserQuestion:
  question: "Set EXECUTE phase to opus?"
  header: "Confirm"
  options:
    - label: "Yes, set to opus"
      description: "Higher cost, maximum capability for implementation"
    - label: "No, keep sonnet (Recommended)"
      description: "Balanced cost and capability"
```

### 4. Handle --reset

Reset to defaults and confirm.

### 5. Show Cost Summary

After any --show or --set, display:
- Estimated tokens per phase (rough approximation)
- Estimated cost per loop at current routing
- Estimated cost at all-opus baseline
- Savings percentage
</steps>

<output_format>
```
=== Multi-Model Orchestration ===

Current routing:
  INIT       → haiku    (fast, cheap)
  UNDERSTAND → sonnet   (balanced)
  PLAN       → sonnet   (balanced) [opus when: security, auth]
  EXECUTE    → sonnet   (balanced)
  VERIFY     → sonnet   (balanced) [opus when: security, auth]
  COMMIT     → haiku    (fast, cheap)
  EVALUATE   → haiku    (fast, cheap)

Keyword overrides:
  "security", "auth", "vulnerability" → PLAN + VERIFY escalate to opus

Cost estimate (per /cs-loop):
  Current routing:   ~$0.08 - $0.45 per loop
  All-opus baseline: ~$0.30 - $1.80 per loop
  Estimated savings: ~75%

To change routing:
  /cs-multi --set EXECUTE=opus     # Use opus for implementation
  /cs-multi --set INIT=sonnet      # Use sonnet for profile detection
  /cs-multi --reset                # Restore defaults
```
</output_format>

<constraints>
- Config is stored in `.claude/state/multi-model.json` (per-project)
- Model routing in /cs-loop is advisory — Claude Code may use different models based on context
- This command configures the documented defaults in the loop, not a runtime override
- Cost estimates are rough approximations only — actual costs depend on token usage
- Never disable or reduce model capability for security-critical tasks (keep security/auth at opus minimum)
</constraints>

<avoid>
## Common Mistakes to Prevent

- **Over-routing to opus**: Don't suggest opus for every phase. The default routing is optimized. Only use opus where reasoning depth truly matters (security, complex architecture).

- **Ignoring keyword overrides**: The keyword override system (security/auth → opus) is a safety net. Don't suggest removing these.

- **Missing validation**: Always validate that phase names and model names are from the allowed sets before writing config.

- **No cost context**: Always show cost estimates when displaying or changing routing. Users need cost context to make informed decisions.

- **Treating as runtime override**: This command configures documented defaults. Inform users that actual model selection may vary based on Claude Code context.
</avoid>

<examples>
## Examples

```
/cs-multi                       # Show current routing
/cs-multi --show                # Same as above
/cs-multi --set EXECUTE=opus    # Use opus for implementation phase
/cs-multi --set COMMIT=sonnet   # Use sonnet for commit phase
/cs-multi --reset               # Restore defaults
```
</examples>

## Notes

- Default routing is optimized for ~75% cost reduction vs all-opus
- Keyword overrides escalate to opus for security-critical tasks automatically
- Model routing docs in `profiles/CLAUDE.md` show the full routing table
- Config persists across sessions in `.claude/state/multi-model.json`
