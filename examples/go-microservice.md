# CLAUDE.md — Go Microservice

> Copy this file to your project root as `CLAUDE.md` to configure Claude Sentient.

## Project Overview

- **Stack:** Go 1.22+, gRPC + Protobuf, PostgreSQL (pgx), Redis
- **Language:** Go
- **Deploy:** Docker + Kubernetes

## Quick Start

```bash
/cs-validate        # Verify Claude Sentient setup
/cs-loop "task"     # Start autonomous development
/cs-assess          # Codebase health audit
```

## Architecture

```
cmd/
  server/             # Main entry point
internal/
  api/
    grpc/             # gRPC service implementations
    http/             # HTTP handlers (health, metrics)
  domain/             # Business logic and domain types
  repository/         # Database access layer
  service/            # Application services
proto/
  service.proto       # Protobuf definitions
  gen/                # Generated code (do not edit)
config/
  config.go           # Config struct loaded from env
migrations/           # SQL migration files (golang-migrate)
Makefile
Dockerfile
```

## Key Patterns

### Project Layout
- Follow standard Go project layout (`cmd/`, `internal/`, `pkg/`)
- `internal/` packages are not importable outside this module
- Dependency injection via constructor functions (no global state)
- Interfaces defined in the package that uses them, not the package that implements

### Error Handling
- Always wrap errors with context: `fmt.Errorf("doing X: %w", err)`
- Define sentinel errors for business logic: `var ErrNotFound = errors.New("not found")`
- Map domain errors to gRPC status codes in the API layer
- Never ignore errors — use `_` only with explicit comment

### gRPC Patterns
- Validate inputs with `buf validate` / `protovalidate`
- Use deadlines: `ctx, cancel := context.WithTimeout(ctx, 5*time.Second)`
- Implement health check: `grpc_health_v1.HealthServer`
- Interceptors for logging, metrics, auth — not inline in handlers

### Database
- Use `pgx` directly (not GORM) for performance
- Repository pattern: `UserRepository` interface + `pgxUserRepository` implementation
- All queries in repository layer — no SQL in services
- Use `golang-migrate` for migrations

## Quality Gates

Before committing:
1. `golangci-lint run` — Must pass (0 errors)
2. `go test ./...` — All tests must pass
3. `go build ./...` — Build must succeed
4. `go vet ./...` — No vet issues

## Hard Rules

1. **No global state** — pass dependencies via constructors
2. **Always handle errors** — no silent `_` without comment
3. **Context propagation** — always accept and pass `context.Context` as first arg
4. **Never generate protobuf manually** — use `make proto`
5. **Table-driven tests** — use `t.Run` subtests for multiple cases

## Makefile Targets

```makefile
make proto      # Regenerate protobuf code
make test       # Run all tests
make lint       # Run golangci-lint
make build      # Build binary
make docker     # Build Docker image
make migrate    # Run database migrations
```
