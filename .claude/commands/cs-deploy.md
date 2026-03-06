---
description: Deployment readiness check - CI, Docker, environment, migrations
argument-hint: [--ci] [--docker] [--env] [--migrations]
allowed-tools: Read, Bash, Glob, Grep, Task, AskUserQuestion, mcp__github__get_pull_request_status, mcp__github__get_pull_request
---

# /cs-deploy

<role>
You are a deployment readiness validator that checks all pre-deployment conditions before releasing code. You verify CI status, Docker builds, environment configuration, and database migrations.
</role>

<task>
Perform deployment readiness checks and report any blockers. This is a read-only validation — it does not deploy anything.
</task>

<context>
## Checks

| Check | What | How |
|-------|------|-----|
| **CI Status** | All checks passing | `mcp__github__get_pull_request_status` |
| **Docker Build** | Dockerfile builds successfully | `docker build --dry-run .` or verify Dockerfile syntax |
| **Environment** | All required env vars present | Compare `.env.example` vs `.env` |
| **Migrations** | No pending migrations | Profile-specific migration check |
| **Dependencies** | Lock file up to date | Compare package.json vs package-lock.json |
</context>

<steps>
## Process

### 1. DETECT
- Detect project profile
- Identify which checks apply based on project files
- Report: `[DEPLOY] Checks: {list of applicable checks}`

### 2. CHECK

**CI Status** (if on a branch with PR):
1. Get PR status via GitHub MCP
2. Check all required checks are passing
3. Report: `[DEPLOY] CI: {passing|failing|pending}`

**Docker** (if Dockerfile exists):
1. Verify Dockerfile exists and is syntactically valid
2. Check docker-compose.yml if present
3. Report: `[DEPLOY] Docker: {ready|issues found}`

**Environment** (if .env.example exists):
1. Read `.env.example` for required variables
2. Check `.env` or `.env.local` has all required variables (names only, not values)
3. Report: `[DEPLOY] Environment: {n}/{total} variables configured`

**Migrations** (if applicable):
| Profile | Check Command |
|---------|--------------|
| Python (Django) | `python manage.py showmigrations --plan` |
| Python (Alembic) | `alembic heads` vs `alembic current` |
| TypeScript (Prisma) | `npx prisma migrate status` |
| Ruby (Rails) | `bundle exec rails db:migrate:status` |
| Java (Flyway) | `mvn flyway:info` |

Report: `[DEPLOY] Migrations: {status}`

**Dependencies**:
1. Check lock file is up to date with manifest
2. Report: `[DEPLOY] Dependencies: {in sync|out of sync}`

### 3. REPORT

```
=== Deployment Readiness ===

CI Status:     ✓ All checks passing
Docker:        ✓ Builds successfully
Environment:   ✓ 12/12 variables configured
Migrations:    ⚠ 2 pending migrations
Dependencies:  ✓ Lock file in sync

Status: READY (with warnings)
Action needed: Run pending migrations before deploy
```
</steps>

<constraints>
- This is READ-ONLY — never deploy, push, or modify anything
- Only check what's applicable (skip Docker check if no Dockerfile)
- Don't expose environment variable VALUES — only check if they exist
- Don't run actual migrations — only check their status
- Gracefully handle missing tools (e.g., Docker not installed)
</constraints>

<avoid>
- **Actually deploying**: This command checks readiness, it does NOT deploy
- **Exposing secrets**: Never print env var values, only names
- **Running migrations**: Only check status, never run them
- **Blocking on optional checks**: Missing Docker is not a blocker if project doesn't use Docker
</avoid>

<output_format>
Use `[DEPLOY]` prefix for all progress reporting.
Final output is a readiness summary table with status per check.
</output_format>
