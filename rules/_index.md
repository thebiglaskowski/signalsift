# Rules Index

> **Path-scoped rules:** These rules are also available in `.claude/rules/` with `paths:` frontmatter. Claude Code automatically loads relevant rules when you work on matching files. The keyword-based loading below is supplementary.

Rules provide topic-specific standards that auto-load based on task context.

## Auto-Loading

During `/cs-loop` INIT, rules are loaded based on task keywords:

| Keywords | Rules Loaded |
|----------|--------------|
| auth, login, password, jwt, oauth | `security`, `api-design` |
| upload, file, multipart, s3, bucket, storage | `security` |
| test, spec, coverage, mock | `testing` |
| api, endpoint, route, rest | `api-design`, `error-handling` |
| database, query, schema, migration | `database` |
| performance, optimize, cache, slow | `performance` |
| ui, component, css, style | `ui-ux-design` |
| react, vue, svelte, angular, next, nuxt | `ui-ux-design` |
| frontend, web, responsive, tailwind | `ui-ux-design` |
| cli, terminal, command | `terminal-ui` |
| docs, readme, changelog | `documentation` |
| refactor, cleanup, quality | `code-quality` |
| git, commit, branch, pr | `git-workflow` |
| log, debug, trace | `logging` |
| debug, bug, fix, reproduce, trace | `logging`, `error-handling` |
| error, exception, catch | `error-handling` |
| prompt, command, xml, template | `prompt-structure` |

## Always-Loaded Rules

These rules load every session regardless of task keywords:

| Rule | Purpose |
|------|---------|
| `anthropic-patterns` | Universal prompt patterns for all Claude interactions |
| `code-quality` | Code quality standards applied to all source code |
| `learnings` | Team-shared decisions, patterns, and learnings |

## Available Rules

| Rule | Focus | When to load |
|------|-------|-------------|
| `security` | OWASP, auth, secrets, validation | Auth flows, file uploads, external API calls, input validation, credential/key management, permission checks |
| `testing` | Coverage, mocks, TDD, naming | Writing/fixing tests, test infrastructure, CI setup, coverage gaps, mocking external services, assertions |
| `api-design` | REST, responses, versioning | Creating/modifying endpoints, request/response schemas, HTTP status codes, API versioning, pagination |
| `database` | Schema, indexes, migrations | Schema changes, query optimization, ORM usage, data migrations, relationship modeling, connection pooling |
| `performance` | Caching, optimization, Web Vitals | Slowness complaints, caching strategies, memory leaks, load optimization, Web Vitals, bundle size |
| `code-quality` | Complexity, naming, dependencies | Refactoring, code reviews, dependency management, complexity reduction, naming conventions, duplication |
| `documentation` | README, changelog, comments | Updating docs, writing changelogs, adding code comments, API documentation, docstrings |
| `git-workflow` | Commits, branches, PRs | Committing changes, branching strategies, PR creation/review, merge conflicts, git hooks |
| `error-handling` | Error types, logging, recovery | Error propagation design, exception handling, retry logic, graceful degradation, fallback behavior |
| `logging` | Structured logs, levels, context | Adding log statements, log format standardization, debugging via logs, observability, tracing |
| `ui-ux-design` | Spacing, typography, a11y | Frontend components, visual design, accessibility audit, responsive layout, CSS/Tailwind work |
| `terminal-ui` | Spinners, colors, progress | CLI output design, terminal formatting, progress indicators, colored output, interactive prompts |
| `prompt-structure` | XML tags, command templates | Writing Claude commands, prompt engineering, CLAUDE.md work, skill/template authoring |

## Usage

Rules auto-load during `/cs-loop`. For manual loading:
```
Load @rules/security for this review
```
