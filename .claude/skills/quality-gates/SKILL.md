---
name: quality-gates
description: Quality gate execution patterns and auto-fix procedures for the VERIFY phase. Covers lint, test, build gate execution, error classification, auto-fix sub-loops, and WebSearch fallback strategies.
user-invocable: false
---

# Quality Gates Skill

Reference material for executing quality gates during `/cs-loop` VERIFY phase.

## Gate Execution Order

| Gate | Action | Pass Criteria |
|------|--------|---------------|
| LINT | Run lint command from profile | Zero errors |
| TEST | Run test command from profile | All tests pass |
| BUILD | Run build command if defined | Clean compilation |
| GIT | Check `git status` | Clean working state |

Advisory gates (report only, non-blocking): TYPE, DOCS, SECURITY.

## Auto-Fix Sub-Loop

When a gate fails, attempt automatic repair (max 3 attempts per gate):

### Error Classification

| Error Type | Fix Strategy |
|------------|-------------|
| Lint (auto-fixable) | Run `fix_command` from profile gates (e.g., `ruff check . --fix`) |
| Import ordering | Run format/sort command from profile gates |
| Type errors | Read file at error location, fix type annotations |
| Test failures | Read failing test + source under test, fix logic in source |
| Build errors | Read compiler output, fix compilation issues |

### Procedure

1. Gate fails -> classify error type from output
2. If profile has `fix_command` for this gate: run it, re-verify
3. If no `fix_command` or it didn't resolve: read error, apply manual fix, re-verify
4. Maximum 3 attempts per gate. Track: `[VERIFY] Auto-fix attempt {n}/3: {gate}`
5. If error count increases after any attempt: revert changes and stop
6. If all 3 attempts fail: fall through to WebSearch strategy

### Hard Constraints

- Never modify test assertions or expected values to make tests pass
- Never skip or disable quality gates
- If fix introduces new errors, revert immediately
- Report each attempt: `[VERIFY] Auto-fix attempt {n}/3: {gate} -- {strategy}`

## WebSearch Fallback

When auto-fix exhausts 3 attempts:

1. Extract error message from gate output
2. WebSearch("{language} {error_message} fix 2026")
3. If solution found: apply fix automatically
4. If still failing after 2 WebSearch attempts: stop and report

## MCP Integration

- **Puppeteer** (web projects): Navigate -> screenshot after UI changes
- **GitHub**: Check CI status on PRs (passing/failing/pending)
- **Vision**: Capture and analyze error screenshots for UI test failures

## CI Monitoring (Post-Commit)

After committing on a branch with a PR:
1. Check if current branch has an open PR
2. If PR exists, monitor CI:
   - Passing -> `[COMMIT] CI passed`
   - Pending -> `[COMMIT] CI running...` (continue)
   - Failing -> Auto-fix if lint/test/type error (max 2 attempts)
   - Infrastructure failure -> Report for manual review
