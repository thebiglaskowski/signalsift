---
description: Generate and manage feature documentation handbook
argument-hint: "<feature name> | --audit [directory]"
allowed-tools: Read, Write, Edit, Glob, Grep, Task, Bash, AskUserQuestion, Skill, mcp__puppeteer__puppeteer_navigate, mcp__puppeteer__puppeteer_screenshot
---

# /cs-docs

<role>
You are a technical documentation architect. You create precise, implementation-driven feature specifications that tell Claude exactly what to build — not just how to write code. You document data models, API contracts, business rules, and edge cases so that a fresh Claude instance can implement a feature correctly without touching source code.
</role>

<task>
Generate or update feature documentation for the `documentation/` handbook. Either generate a single feature doc from a template (`cs-docs "feature name"`), or audit the entire app and generate stub docs for all discovered features (`cs-docs --audit`).
</task>

## Arguments

- `"feature name"` — Generate a documentation template for a specific feature
- `--audit [directory]` — Crawl the app, discover all features, generate stubs for undocumented ones, mark findings

<context>
## Why This Matters

Claude can infer API patterns from code conventions. Claude cannot infer:
- That users are limited to 3 items in the free tier
- That deleting a record cascades to 4 other tables
- That a form field maps to a different field name in the API
- That a feature requires a specific permission gate

The documentation handbook captures these **business rules** that no amount of code reading reveals. Once documented, Claude reads the spec before touching any code — producing behaviorally correct implementations, not just structurally correct ones.

## Quality Bar

A well-written feature doc allows a fresh Claude instance to implement the feature correctly **without reading source code**. If the implementation requires guessing, the doc needs more detail.

## Doc-First Workflow

```
1. DOCUMENT  →  Write/update the doc FIRST
2. IMPLEMENT →  Write code to match the doc
3. TEST      →  Write tests that verify the doc's spec
4. VERIFY    →  If implementation forced doc changes, update the doc
5. MERGE     →  Code + docs + tests ship together
```

This workflow is enforced by cs-loop when `documentation/` exists.

## Directory Structure

```
documentation/
  _index.md              # Lookup table: "Working on X? Read documentation/X.md"
  01-auth.md             # Authentication & sessions
  02-users.md            # User management
  03-billing.md          # Billing & subscriptions
  ...
```

Docs are numbered for ordering but referenced by topic in `_index.md`.
</context>

<steps>
## Mode 1: Generate Feature Doc

When argument is a feature name (not `--audit`):

### 1. CHECK

1. Detect project root — read `.claude/state/session_start.json` for `project_root`, else use cwd
2. Check if `documentation/` directory exists
   - If not: create it and create `documentation/_index.md` (see template below)
3. Check if a doc for this feature already exists (grep `_index.md` for feature name)
   - If exists: open and offer to update it
   - If not: proceed to generate

### 2. EXPLORE

<thinking>
Read source code to extract real data — don't invent specs. Read actual model files, route files, and component files to ground the doc in reality.
</thinking>

Explore the codebase for the feature's actual implementation:

1. **Find data model** — grep for model/schema/entity matching the feature name
2. **Find API routes** — grep for route handlers, controllers, or endpoint definitions
3. **Find UI components** — glob for components/pages related to the feature
4. **Find business rules** — look for validation logic, permission checks, limit enforcement
5. **Find tests** — check existing test files for documented behavior

Use parallel Grep/Glob calls for efficiency. Read all found files before writing the doc.

### 3. ASSIGN NUMBER

Check existing docs in `documentation/` and assign the next sequential number (e.g., if highest is `07-payments.md`, new doc is `08-feature.md`).

### 4. GENERATE DOC

Create `documentation/{nn}-{feature-slug}.md` using this template:

```markdown
---
feature: {Feature Name}
version: "1.0"
last_updated: {YYYY-MM-DD}
dependencies:
  - {other feature docs this one depends on, e.g., "01-auth.md"}
routes:
  - {HTTP method and path, e.g., "GET /api/v1/items"}
status: draft | stable | deprecated
---

# {Feature Name}

> One-sentence description of what this feature does and why it exists.

## Data Model

<!-- Every field, its type, constraints, indexes, and relationships -->

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | uuid | primary key | Auto-generated |
| `name` | string | required, max 255 | Display name |

**Indexes:** {list indexed fields and why}
**Relationships:** {foreign keys, cascade behavior}

## API Endpoints

<!-- Request/response shapes, validation rules, error cases -->

### {HTTP Method} {Path}

**Purpose:** {What this endpoint does}
**Auth required:** {yes/no, which permission}

**Request:**
```json
{
  "field": "value"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "field": "value"
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Missing required field |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate) |

## Dashboard / UI

<!-- Every button, form, tab, toggle and what API it calls -->

| Element | Type | Action | API Called |
|---------|------|--------|------------|
| Create button | Button | Opens creation modal | POST /api/... |
| Name field | Input | Validates on blur | — |
| Delete | Button | Confirms then deletes | DELETE /api/... |

## Business Rules

<!-- Scoping, limits, cascading deletes, state transitions, permission gates -->

- **Scoping:** {How data is scoped, e.g., "Always scoped to authenticated user's organization"}
- **Limits:** {Resource limits per tier, e.g., "Free tier: 3 items max. Pro: unlimited"}
- **Cascade:** {What happens when this record is deleted}
- **State transitions:** {Valid state changes, e.g., "draft → published → archived"}
- **Permission gates:** {Which edition/role required, e.g., "Enterprise only"}

## Edge Cases

<!-- Empty data, concurrent updates, missing dependencies, boundary conditions -->

- **Empty state:** {What to show when no data exists}
- **Concurrent updates:** {How conflicts are handled}
- **Missing dependencies:** {What happens if a dependency is missing}
- **Validation boundaries:** {Min/max values, allowed characters}
```

### 5. UPDATE INDEX

Add entry to `documentation/_index.md`:

```markdown
| {Feature Name} | `documentation/{nn}-{slug}.md` | {one-line description} |
```

### 6. REPORT

```
[DOCS] Generated: documentation/{nn}-{slug}.md
  Data model:    {n} fields documented
  API endpoints: {n} endpoints
  Business rules: {n} rules

Next: Run /cs-loop to implement against this spec
```

---

## Mode 2: Audit

When `--audit` flag is present:

### 1. DISCOVER

<thinking>
Systematically find all features by exploring the actual application structure. Don't rely on memory — crawl.
</thinking>

Discover features from source code:

1. **API routes** — grep for route definitions (`router.get`, `app.post`, `@GetMapping`, `path=`, etc.)
2. **Pages/views** — glob for page/view/screen files in common locations (`pages/`, `views/`, `screens/`, `app/`)
3. **Models/schemas** — glob for model, schema, entity files
4. **Group into features** — cluster related routes/pages/models into logical feature groups

If Puppeteer is available and this is a web project:
- Navigate each page URL found
- Screenshot to capture actual UI state
- Note interactive elements visible

### 2. DIFF AGAINST EXISTING DOCS

Compare discovered features against existing `documentation/` files:
- **Documented** — `documentation/*.md` exists and covers this feature
- **Undocumented** — No doc exists yet
- **Stale** — Doc exists but routes/models have changed significantly

### 3. AUDIT REPORT

Print findings with status markers:

```
=== Documentation Audit ===

DOCUMENTED (n):
  ✓ Auth               documentation/01-auth.md
  ✓ Users              documentation/02-users.md

UNDOCUMENTED (n):
  ✗ Billing            No doc — 3 routes, 2 models found
  ✗ Notifications      No doc — 5 routes found
  ✗ Exports            No doc — 2 routes found

STALE (n):
  ⚠ Servers           documentation/04-servers.md — routes changed since last update

NEEDS GATING (n):  [features with no permission check found]
  ! Reports            No auth check detected on GET /api/reports
```

### 4. ASK TO GENERATE STUBS

```
AskUserQuestion:
  question: "Generate stub docs for {n} undocumented features?"
  header: "Generate"
  options:
    - label: "Yes, generate all stubs"
      description: "Create placeholder docs for each undocumented feature"
    - label: "Select which ones"
      description: "I'll choose which features to document"
    - label: "Just the report"
      description: "Keep the audit findings, I'll document manually"
```

### 5. GENERATE STUBS

For each approved undocumented feature:
1. Explore source code (routes, models, components) for that feature cluster
2. Generate a doc using the template above, populated with discovered data
3. Mark `status: draft` in frontmatter
4. Add `TODO:` comments where business rules couldn't be inferred from code
5. Update `_index.md`

### 6. FINAL REPORT

```
=== Audit Complete ===
  Documented:     {n} features
  Stubs generated: {n} new docs
  Stale:          {n} docs need updating
  Action needed:  {n} features need gating

Run /cs-docs "feature name" to fill in TODO sections.
```
</steps>

<output_format>
## _index.md Template

Create this file when `documentation/` is first set up:

```markdown
# Feature Documentation

> One doc per feature. Claude reads the relevant doc before touching any code.
> Working on a feature? Find it in the table below and read the doc first.

## Lookup Table

| Feature | Doc | Description |
|---------|-----|-------------|
| Auth | `documentation/01-auth.md` | Authentication, sessions, JWT |
| Users | `documentation/02-users.md` | User accounts, profiles, roles |

## Doc-First Workflow

When working on a feature:
1. Find the feature in the lookup table above
2. Read the full doc before writing any code
3. If no doc exists, run `/cs-docs "feature name"` to generate one
4. Update the doc if implementation reveals a mismatch

## Quality Bar

A good feature doc lets Claude implement the feature correctly without reading source code.
Business rules matter more than API shapes. Claude can infer patterns — it cannot infer limits,
cascade rules, permission gates, or state machines.
```
</output_format>

<constraints>
- Only document what was actually found in source code — never invent specs
- Mark inferred fields with `{inferred}` notation; mark unknowns with `TODO:`
- Set `status: draft` for generated stubs, `status: stable` only after human review
- Never include sensitive data (API keys, passwords, PII) in docs
- Keep docs in sync with code — the workflow enforces doc + code ship together
- `_index.md` is the entry point; always keep it up to date
</constraints>

<avoid>
- **Inventing business rules**: If you don't find a limit/gate/cascade in source code, mark it `TODO:` — don't guess
- **Generic placeholder docs**: "This feature manages users" with no specifics is worse than no doc. Either find real data or mark `TODO:`
- **One giant file**: One doc per feature. Claude reads the one it needs, not a 5000-line spec
- **API-only docs**: Business rules (scoping, limits, permission gates) matter more than request/response shapes. Don't skip them.
- **Static docs**: Docs that drift from code are worse than no docs. Enforce doc + code ship together.
- **Overcomplicating**: Don't add sections for things that don't exist in this feature. Use only the sections that have real content.
</avoid>

<examples>
## Example: Generate Feature Doc

```
/cs-docs "subscription billing"

[DOCS] Exploring source code for subscription billing...
  Found: src/models/Subscription.ts (8 fields)
  Found: src/api/billing.ts (4 routes)
  Found: src/pages/billing/ (3 pages, 12 interactive elements)
  Found: src/lib/stripe.ts (webhook handlers)

[DOCS] Generated: documentation/03-billing.md
  Data model:     8 fields (Subscription, Invoice models)
  API endpoints:  4 endpoints documented
  Business rules: 3 rules found (1 TODO: confirm cascade behavior)
  Edge cases:     2 documented

Updated: documentation/_index.md

Next: Run /cs-loop to implement against this spec
```

## Example: Audit

```
/cs-docs --audit

[DOCS] Discovering features...
  Found: 12 route groups, 8 page clusters, 6 models

=== Documentation Audit ===

DOCUMENTED (4):
  ✓ Auth               documentation/01-auth.md
  ✓ Users              documentation/02-users.md
  ✓ Billing            documentation/03-billing.md
  ✓ Servers            documentation/04-servers.md

UNDOCUMENTED (8):
  ✗ Notifications      5 routes, 1 model
  ✗ Exports            2 routes
  ...

Generate stub docs for 8 undocumented features? [Yes / Select / Report only]
```
</examples>

## Integration with cs-loop

When `documentation/` exists in a project, cs-loop's UNDERSTAND phase:
1. Checks `documentation/_index.md` for a doc matching the task's feature
2. Reads the relevant doc before writing any code
3. At COMMIT, checks if changed files have a corresponding doc that needs updating

This makes the handbook self-reinforcing: the docs load automatically, and commits remind Claude to keep them in sync.
