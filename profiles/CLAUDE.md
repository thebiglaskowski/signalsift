# Profiles — Claude Sentient

> Context for working on language profile YAML files.

## Profile Detection

Sentient auto-detects project type by scanning for indicator files:

| Profile | Detected By | Lint | Test | Build |
|---------|-------------|------|------|-------|
| Python | `pyproject.toml`, `*.py`, `*.ipynb` | ruff check | pytest | python -m build |
| TypeScript | `tsconfig.json`, `*.ts` | eslint | vitest | tsc |
| Go | `go.mod`, `*.go` | golangci-lint run | go test ./... | go build ./... |
| Rust | `Cargo.toml` | cargo clippy | cargo test | cargo build |
| Java | `pom.xml`, `build.gradle` | mvn checkstyle:check | mvn test | mvn compile |
| C/C++ | `CMakeLists.txt`, `Makefile` | clang-tidy | ctest | cmake --build build |
| Ruby | `Gemfile` | rubocop | rspec | — |
| Shell | `*.sh`, `*.ps1` | shellcheck | — | — |
| General | (fallback) | auto-detect | auto-detect | auto-detect |

---

## Profile YAML Structure

Every profile must have these fields:

```yaml
name: python
description: Python project profile
version: "1.0"

detection:
  files: [pyproject.toml, setup.py, requirements.txt]
  extensions: [.py, .pyi]

gates:
  lint:
    command: ruff check .
    detect: pyproject.toml
  test:
    command: pytest
    detect: tests/
  build:
    command: python -m build
    detect: pyproject.toml

conventions:
  naming: snake_case
  # ... language-specific conventions
```

### Gate Structure

All gates use standardized keys:

| Key | Purpose |
|-----|---------|
| `command` | Primary command to run |
| `fix_command` | Auto-fix command (used by VERIFY auto-fix sub-loop) |
| `alternative` | Fallback if primary tool not available |
| `detect` | File/dir that indicates this gate applies |

**Auto-fix support:** Profiles with `fix_command` on lint gates enable the VERIFY auto-fix sub-loop:
- Python: `ruff check . --fix`
- TypeScript: `npx eslint . --fix`
- Go: `golangci-lint run --fix`
- Rust: `cargo clippy --fix --allow-dirty`
- Ruby: `bundle exec rubocop -a`
- C++: `clang-tidy --fix`

---

## Model Routing

Models are automatically selected by phase for cost optimization:

| Phase | Model | Rationale |
|-------|-------|-----------|
| INIT | haiku | Fast context loading |
| UNDERSTAND | sonnet | Standard analysis |
| PLAN | sonnet/opus | opus for "security" keywords |
| EXECUTE | sonnet | Code generation |
| VERIFY | sonnet | Quality checks |
| COMMIT | haiku | Simple git operations |
| EVALUATE | haiku | Quick assessment |

**Override triggers:**
- Task contains "security", "auth", "vulnerability" → opus for PLAN and VERIFY

---

## Web Project Detection

Profiles can include `web_indicators` for auto-loading UI/UX rules:

| Indicators | Profile | Auto-loaded Rule |
|------------|---------|-----------------|
| next.config, vite.config, react, vue, svelte | TypeScript Web | ui-ux-design |
| templates/, django, flask, jinja2 | Python Web | ui-ux-design |

---

## Infrastructure Detection

Profiles can include optional `infrastructure` sections for Docker, CI, and platform detection:

```yaml
infrastructure:
  docker:
    indicators: [Dockerfile, docker-compose.yml]
    commands:
      build: docker build -t {project_name} .
      up: docker-compose up -d
      test: docker-compose run --rm app {test_command}
  ci:
    indicators: [.github/workflows/, .gitlab-ci.yml]
    type: auto-detect
```

Used by `/cs-deploy` for deployment readiness checks.

---

## Adding a New Profile

1. Create `profiles/{language}.yaml` with required fields
2. Add detection rules (files + extensions)
3. Define gates (lint, test, build minimum — include `fix_command` if available)
4. Add conventions section
5. Add `models` and `thinking` sections
6. Optionally add `infrastructure` section
7. Run `node profiles/__tests__/test-profiles.js` to validate
