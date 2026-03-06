# CLAUDE.md — Django REST API + Celery

> Copy this file to your project root as `CLAUDE.md` to configure Claude Sentient.

## Project Overview

- **Stack:** Django 5.x, Django REST Framework, Celery + Redis, PostgreSQL
- **Language:** Python 3.12+
- **Deploy:** Docker + Gunicorn/Uvicorn

## Quick Start

```bash
/cs-validate        # Verify Claude Sentient setup
/cs-loop "task"     # Start autonomous development
/cs-assess          # Codebase health audit
```

## Architecture

```
src/
  config/               # Django settings (base, dev, prod, test)
  apps/
    users/              # Custom user model, auth views
    api/                # DRF viewsets, serializers, routers
    tasks/              # Celery task definitions
  core/
    models.py           # Abstract base models (TimeStampedModel, etc.)
    permissions.py      # Custom DRF permissions
    exceptions.py       # Custom exception handlers
  celery.py             # Celery application configuration
manage.py
pyproject.toml
docker-compose.yml
```

## Key Patterns

### Django Models
- Inherit from `TimeStampedModel` (provides `created_at`, `updated_at`)
- UUID primary keys for all public-facing models
- `select_related` / `prefetch_related` to avoid N+1 queries
- Always write migrations — never edit existing ones in production

### DRF API Design
- ViewSets over APIViews for CRUD resources
- Serializers validate all input — never trust raw `request.data`
- Consistent response format: `{ "data": ..., "meta": ... }` for lists
- Version the API via URL prefix: `/api/v1/`
- Use `django-filter` for list filtering, not custom query logic

### Celery Tasks
- All tasks must be idempotent (safe to retry)
- Use `task_id` parameter for deduplication
- `@shared_task(bind=True, max_retries=3)` pattern
- Store task results in `django-celery-results`
- Monitor with Flower in development

### Authentication
- JWT via `djangorestframework-simplejwt`
- Refresh tokens stored in HttpOnly cookies
- Custom `IsOwner` permission for object-level access

## Environment

Claude Sentient auto-detects the Python environment. Prefer:
- `poetry` for dependency management
- `python-decouple` for environment variables

## Quality Gates

Before committing:
1. `ruff check .` — Linting must pass
2. `ruff format --check .` — Formatting must match
3. `mypy src/` — Type checking must pass
4. `pytest` — All tests must pass (minimum 80% coverage)
5. `python manage.py check --deploy` — Deployment checks

## Hard Rules

1. **Never use `DEBUG=True` in production** — use `python-decouple`
2. **Always paginate list endpoints** — never return unbounded querysets
3. **Index foreign keys** — run `python manage.py check` to catch missing indexes
4. **Validate at the serializer level** — never in the view
5. **Celery tasks are always idempotent** — assume any task may run twice

## Environment Variables

Required (use `python-decouple` or `.env`):
```
DATABASE_URL=postgres://...
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=
CELERY_BROKER_URL=
```
