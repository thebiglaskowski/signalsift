# CLAUDE.md — Rust API with Axum

> Copy this file to your project root as `CLAUDE.md` to configure Claude Sentient.

## Project Overview

- **Stack:** Rust (stable), Axum, SQLx + PostgreSQL, Tower middleware
- **Language:** Rust
- **Deploy:** Docker (scratch image)

## Quick Start

```bash
/cs-validate        # Verify Claude Sentient setup
/cs-loop "task"     # Start autonomous development
/cs-assess          # Codebase health audit
```

## Architecture

```
src/
  main.rs             # Application entry point
  config.rs           # Configuration from environment
  error.rs            # Unified error type
  routes/
    mod.rs            # Router construction
    users.rs          # /users handlers
    health.rs         # /health handler
  models/             # Domain types and DTOs
  db/
    mod.rs            # Database pool setup
    queries/          # SQLx query functions
  middleware/         # Auth, tracing, rate limiting
migrations/           # SQLx migration files
Cargo.toml
Dockerfile
```

## Key Patterns

### Error Handling
- Single `AppError` enum that implements `IntoResponse`
- Wrap third-party errors with `#[from]` derive
- Never use `unwrap()` in request handlers — always return `Result`
- Use `?` for error propagation, not explicit `match`

### Axum Patterns
- Extractors for all inputs: `Path<T>`, `Query<T>`, `Json<T>`, `State<T>`
- Validated DTOs with `validator` crate
- Layered middleware via `ServiceBuilder`
- Shared state via `Arc<AppState>` — wrap in `Extension` or use `.with_state()`

### SQLx
- Compile-time checked queries with `sqlx::query!` macro
- Connection pool via `PgPool` — never open per-request connections
- All migrations in `migrations/` — run with `sqlx migrate run`
- Test with `#[sqlx::test]` attribute for database integration tests

### Async Patterns
- Tokio runtime — never block the async thread
- Use `spawn_blocking` for CPU-intensive work
- `Arc<Mutex<T>>` only when necessary — prefer message passing

## Quality Gates

Before committing:
1. `cargo clippy -- -D warnings` — Must pass with 0 warnings
2. `cargo test` — All tests must pass
3. `cargo build --release` — Release build must succeed
4. `cargo fmt --check` — Formatting must match

## Hard Rules

1. **No `unwrap()` in handlers** — always use `?` or explicit error handling
2. **No `unsafe` blocks** — without a detailed safety comment explaining why
3. **Connection pool always** — never per-request database connections
4. **Validate all inputs** — use `validator` derive macros on DTOs
5. **Document public API** — `///` doc comments on all public items

## Environment Variables

```
DATABASE_URL=postgres://...
REDIS_URL=redis://localhost:6379
PORT=3000
LOG_LEVEL=info
JWT_SECRET=
```

## Cargo Features

Keep binary size small:
- Default features only unless explicitly needed
- Use `cargo-audit` in CI for dependency vulnerability scanning
- Prefer `tokio` ecosystem crates for consistency
