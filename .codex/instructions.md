# Claude Sentient — OpenAI Codex CLI Instructions

This project uses Claude Sentient, an autonomous development orchestration layer for Claude Code.

## Project Overview

- **Type**: Markdown commands + JavaScript hooks + YAML profiles + JSON schemas
- **Stack**: Node.js (no dependencies), shell scripts (bash + PowerShell)
- **Tests**: Node.js `assert` module, 943 total tests across 6 suites

## Code Conventions

### General
- Functions ≤ 50 lines, nesting depth ≤ 3
- Named constants for magic values
- Early returns to reduce nesting
- No external dependencies — pure Node.js built-ins only

### JavaScript (hooks — .cjs files)
- CommonJS modules (`.cjs` extension required for ESM compatibility)
- All hooks export nothing, read stdin as JSON, write JSON to stdout
- Use `utils.cjs` for shared utilities (getProjectRoot, appendCapped, pruneDirectory)
- `validateFilePath()` on any user-supplied path before file operations

### YAML Files (agents, profiles)
- No YAML library — tests use line-based regex parsing
- Required fields in agents: name, description, version, role, expertise, spawn_prompt, quality_gates
- Required fields in profiles: name, version, language, detect, lint, test

### Markdown Files (commands)
- YAML frontmatter with: description, argument-hint, allowed-tools
- XML tags for structure: `<role>`, `<task>`, `<steps>`, `<avoid>`, `<output_format>`

## Running Tests

```bash
node profiles/__tests__/test-profiles.js
node .claude/hooks/__tests__/test-hooks.js
node .claude/commands/__tests__/test-commands.js
node agents/__tests__/test-agents.js
node schemas/__tests__/test-schemas.js
node integration/__tests__/test-integration.js
```

## Key Constraints

- **No YAML library**: All YAML parsing is line-based regex in test files
- **No test framework**: Uses Node.js `assert` module with custom `test()` / `suite()` wrappers
- **Integration tests enforce parity**: install.sh and install.ps1 must have identical component lists
- **Version consistency**: CLAUDE.md, README.md, all profile YAML, and agents YAML must share the same version
- **Hook self-protection**: `file-validator.cjs` blocks edits to `.claude/hooks/*.cjs` during active sessions

## Directory Structure

```
.claude/
  commands/     cs-*.md slash commands (15 total)
  hooks/        *.cjs session lifecycle hooks (13 total)
  rules/        *.md always-loaded and path-scoped rules
  state/        runtime state files (not committed)
agents/         YAML agent role definitions (9 total)
profiles/       YAML language profiles (9 total)
schemas/        JSON schemas for validation (12 total)
examples/       Project CLAUDE.md templates
rules/          Canonical rule copies (synced with .claude/rules/)
templates/      Governance file templates
```
