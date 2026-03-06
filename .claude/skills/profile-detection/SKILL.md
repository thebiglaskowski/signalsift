---
name: profile-detection
description: Profile and environment detection for the INIT phase. Covers session state loading, Python environment detection (conda/venv/poetry/pdm), web project detection, rule auto-loading, and MCP context gathering.
user-invocable: false
---

# Profile Detection Skill

Reference material for the `/cs-loop` INIT phase — detecting project profile, environment, and loading context.

## Session State Recovery

1. **Compaction recovery** — Check `.claude/state/compact-context.json` (written by pre-compact hook). If present, restore current task ID, recent file changes, decisions, and phase context.

2. **Profile loading** — Read `.claude/state/session_start.json` (created by session-start hook). Use the `profile` field. If missing or stale, fall back to scanning for project indicator files (see `profiles/CLAUDE.md`). For gate commands, read `profiles/{name}.yaml`.

## Python Environment Detection

| Indicator | Environment | Command Prefix |
|-----------|-------------|----------------|
| `environment.yml` | Conda | `conda run -n <env> --no-capture-output` |
| `.venv/`, `venv/` | Virtualenv | Activate first or use `.venv/bin/python` |
| `poetry.lock` | Poetry | `poetry run` |
| `pdm.lock` | PDM | `pdm run` |

Report: `[INIT] Environment: conda (myenv)` or `[INIT] Environment: system python`

## Web Project Detection

| Indicators | Profile | Auto-load |
|------------|---------|-----------|
| next.config, vite.config, react, vue, svelte | TypeScript Web | ui-ux-design |
| templates/, django, flask, jinja2 | Python Web | ui-ux-design |

## Rule Auto-Loading

Rules with `paths:` frontmatter in `.claude/rules/` are loaded automatically by Claude Code based on file context. For supplementary keyword-based loading, see `rules/_index.md` for the full keyword-to-rule mapping.

## MCP Context Gathering

| Server | What to Load | When |
|--------|-------------|------|
| **context7** | Library docs for detected imports | Always (scan task-related files) |
| **github** | Issue/PR requirements, recent commits | When task references #issues or PRs |
| **memory** | Prior decisions/patterns matching task keywords | Always (search nodes) |
| **memory** | Cross-project global/org learnings | Always (search scope:global, scope:org) |

## Dependency Changelogs

Trigger keywords: "update", "upgrade", "migrate", "bump". Use WebFetch to load CHANGELOG.md or release notes for the dependency being changed. Prevents breaking changes from surprising you.

## Governance Files

Check these exist, create from `templates/` if missing: `STATUS.md`, `CHANGELOG.md`, `DECISIONS.md`, `.claude/rules/learnings.md`.

Check for `CLAUDE.md` — if missing, report: `[INIT] No CLAUDE.md found. Run /cs-init to create context architecture.`
