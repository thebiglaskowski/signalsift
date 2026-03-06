# CLAUDE.md — Next.js + Supabase + Stripe

> Copy this file to your project root as `CLAUDE.md` to configure Claude Sentient.

## Project Overview

- **Stack:** Next.js 15 (App Router), Supabase (Postgres + Auth + Storage), Stripe payments
- **Language:** TypeScript
- **Deploy:** Vercel

## Quick Start

```bash
/cs-validate        # Verify Claude Sentient setup
/cs-loop "task"     # Start autonomous development
/cs-assess          # Codebase health audit
```

## Architecture

```
src/
  app/                    # Next.js App Router pages and layouts
    (auth)/               # Auth group: login, signup, reset
    (dashboard)/          # Protected dashboard routes
    api/                  # API route handlers
  components/             # Shared UI components
  lib/
    supabase/             # Supabase client and server utilities
    stripe/               # Stripe client and webhook handlers
  types/                  # TypeScript types and Zod schemas
supabase/
  migrations/             # SQL migration files
  seed.sql                # Development seed data
```

## Key Patterns

### Supabase Auth
- Use `createServerClient` in Server Components and API routes
- Use `createBrowserClient` in Client Components
- Middleware at `src/middleware.ts` handles session refresh and redirects
- Row Level Security (RLS) policies enforce data access — always enable RLS

### Stripe Payments
- Webhooks at `/api/webhooks/stripe` — verify signature with `stripe.webhooks.constructEvent`
- Store `stripe_customer_id` and `subscription_status` on user profiles
- Sync subscription state via webhook, not client-side

### Database Conventions
- All tables use UUID primary keys
- `created_at` and `updated_at` timestamps on every table
- Foreign keys always have indexes
- Use RLS policies, not application-level filtering

### API Routes
- Validate all inputs with Zod
- Return consistent `{ data, error }` shapes
- Use `NextResponse.json()` — never raw `Response`

## Quality Gates

Before committing:
1. `pnpm lint` — ESLint must pass with 0 errors
2. `pnpm type-check` — `tsc --noEmit` must pass
3. `pnpm test` — Vitest unit tests must pass
4. `pnpm build` — Production build must succeed

## Hard Rules

1. **Never expose service role key** — only use in server-only code (`'use server'` or API routes)
2. **Always enable RLS** — every table must have RLS policies before shipping
3. **Validate Stripe webhooks** — always verify `stripe-signature` header
4. **Type all Supabase queries** — use generated types from `supabase gen types`
5. **Test in preview** — use Vercel preview deployments for feature branches

## Environment Variables

Required in `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=     # server-only
STRIPE_SECRET_KEY=              # server-only
STRIPE_WEBHOOK_SECRET=          # server-only
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
```

## MCP Servers

Recommended for this stack:
- `context7` — Next.js, Supabase, Stripe documentation
- `github` — PR creation and issue linking
