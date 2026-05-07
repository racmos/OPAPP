# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Improve accessibility, a11y audit, WCAG compliance, screen reader support, keyboard navigation, make accessible | accessibility | /home/racmos/OPAPP/.agents/skills/accessibility/SKILL.md |
| Build RESTful APIs, microservices, lightweight web services with Flask | flask-api-development | /home/racmos/OPAPP/.agents/skills/flask-api-development/SKILL.md |
| Build web components, pages, artifacts, applications, styling/beautifying any web UI | frontend-design | /home/racmos/OPAPP/.agents/skills/frontend-design/SKILL.md |
| Python data validation, type hints, runtime type checking, FastAPI/Django/config management | pydantic | /home/racmos/OPAPP/.agents/skills/pydantic/SKILL.md |
| Execute Python code, data processing, web scraping, image processing, automation | python-executor | /home/racmos/OPAPP/.agents/skills/python-executor/SKILL.md |
| Pythonic idioms, PEP 8, type hints, best practices | python-patterns | /home/racmos/OPAPP/.agents/skills/python-patterns/SKILL.md |
| Write Python tests, pytest, fixtures, mocking, TDD | python-testing-patterns | /home/racmos/OPAPP/.agents/skills/python-testing-patterns/SKILL.md |
| Improve SEO, optimize for search, fix meta tags, add structured data, sitemap | seo | /home/racmos/OPAPP/.agents/skills/seo/SKILL.md |
| SQLAlchemy ORM, Alembic migrations, database schemas, query optimization | sqlalchemy-orm | /home/racmos/OPAPP/.agents/skills/sqlalchemy/SKILL.md |
| SQLAlchemy models, Alembic migrations, database schema changes, query optimization | sqlalchemy-alembic-expert | /home/racmos/OPAPP/.agents/skills/sqlalchemy-alembic-expert-best-practices-code-review/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### accessibility
- WCAG 2.2 compliance target: AA minimum, AAA where feasible
- All images MUST have alt text; decorative images use `alt="" role="presentation"`
- Color contrast: 4.5:1 for normal text, 3:1 for large text, 3:1 for UI components
- Never rely on color alone for meaning — add icons + text
- All interactive elements keyboard accessible (Tab, Enter, Space)
- Focus visible with `:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px }`
- Never use `*:focus { outline: none }` globally
- Target size minimum 24×24px (AA), recommended 44×44px
- Form labels must be programmatically associated (`<label for="id">` or implicit)
- Error handling: `aria-invalid="true"`, `aria-describedby`, `role="alert"`, focus first error
- Skip links for keyboard users to bypass navigation
- Respect `prefers-reduced-motion` — disable animations/transitions
- Page language declared: `<html lang="en">`
- Prefer native elements over ARIA roles (button over div role="button")

### flask-api-development
- Use blueprints for modular organization, never global state
- Validate ALL user input before processing
- Use SQLAlchemy ORM for database operations with proper transactions
- Return appropriate HTTP status codes (200, 201, 400, 401, 404, 500)
- Implement pagination for collection endpoints
- Log errors and important events, never return stack traces in production
- Use environment variables for all configuration and secrets
- NEVER store secrets in code (passwords, API keys, JWT secrets)
- Use CORS properly with explicit allowlists
- Implement comprehensive error handlers for all expected exceptions

### frontend-design
- Choose distinctive fonts — never generic Arial/Inter/Roboto/system fonts
- Use CSS variables for color consistency and theming
- Dominant colors with sharp accents — no timid, evenly-distributed palettes
- Use CSS animations for micro-interactions; respect `prefers-reduced-motion`
- One well-orchestrated page load animation > scattered micro-interactions
- Spatial composition: asymmetry, overlap, diagonal flow, grid-breaking elements
- Backgrounds need atmosphere: gradient meshes, noise textures, layered transparencies
- NEVER use generic AI aesthetics: purple gradients on white, cookie-cutter components
- Match implementation complexity to aesthetic vision — maximalist needs elaborate code
- Bold direction and intentionality over safe/generic choices

### pydantic
- Use `BaseModel` with `ConfigDict` for validation settings
- `Field(...)` for constraints: `min_length`, `max_length`, `ge`, `le`, `pattern`
- `@field_validator` for cross-field and custom validation
- `model_dump()` for serialization (not `.dict()` in v2)
- Automatic type coercion: strings → ints, etc.
- `EmailStr`, `HttpUrl` for validated string types
- Use `Annotated[T, Field(...)]` for modern type hinting
- Handle `ValidationError` explicitly with `.errors()` for user-friendly messages

### python-executor
- Use for data processing, web scraping, image/video manipulation, automation
- Pre-installed: NumPy, Pandas, Matplotlib, requests, BeautifulSoup, Pillow, OpenCV
- Always handle exceptions and validate inputs
- Use context managers for resources (files, network connections)
- Prefer list/dict comprehensions for simple transforms
- Use generators for lazy evaluation with large datasets

### python-patterns
- Readability first — clear names, obvious structure
- EAFP over LBYL: try/except instead of excessive if-checks
- Type hints on ALL function signatures; use Python 3.9+ built-in types
- Specific exception handling — never bare `except:`
- Exception chaining: `raise CustomError("msg") from e`
- Context managers (`with`) for all resource management
- List/dict comprehensions for simple transforms; generators for lazy eval
- `functools.wraps` on all decorators
- NEVER: mutable default args, `type()` instead of `isinstance()`, `== None`, `from module import *`
- Use `pathlib.Path` for path operations, f-strings for formatting

### python-testing-patterns
- AAA pattern: Arrange-Act-Assert in every test
- One behavior per test — never test multiple things in one function
- Use pytest fixtures for setup/teardown; scope appropriately
- `@pytest.mark.parametrize` for multiple similar test cases
- `unittest.mock.patch` for external dependencies
- `pytest.raises(Exception, match="msg")` for exception testing
- Test error paths, not just happy paths
- Naming: `test_<unit>_<scenario>_<expected>`
- Use markers (`@pytest.mark.slow`, `@pytest.mark.integration`) for test categorization
- Aim for meaningful coverage, not just high percentages

### seo
- Add `<meta name="robots" content="index, follow">` to all public pages
- Use canonical URLs: `<link rel="canonical" href="...">` to prevent duplicate content
- Create XML sitemap with lastmod, changefreq, priority
- Add structured data (JSON-LD) for rich snippets
- Optimize meta tags: unique `<title>` (50-60 chars) and `<meta name="description">` (150-160 chars)
- Open Graph tags for social sharing: `og:title`, `og:description`, `og:image`
- Ensure fast load times and mobile-friendly design

### sqlalchemy-orm
- SQLAlchemy 2.0 API: use `select()`, `Mapped[T]`, `mapped_column()`
- Type hints on all model columns: `Mapped[Optional[str]] = mapped_column(String(255))`
- Use `relationship()` with `back_populates` for bidirectional relationships
- `server_default=func.now()` for timestamps, not Python `datetime.now()`
- Use explicit transactions: `with Session(engine) as session: ... session.commit()`
- `selectinload()` for eager loading to avoid N+1 queries
- Use `unique=True, index=True` for searchable columns
- NEVER use string-based query concatenation — always parameterized queries

### sqlalchemy-alembic-expert
- Alembic for all schema migrations, never manual DDL in production
- One migration per logical change, descriptive revision messages
- Test migrations against production-like data volumes
- Use `op.batch_alter_table()` for SQLite-compatible column changes
- Add `create_index()`/`drop_index()` in separate migrations from table changes
- Review generated migration scripts before applying
- Use `--autogenerate` for initial schema, manual review for data migrations
- Always backup database before applying migrations in production

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | /home/racmos/OPAPP/AGENTS.md | Main project conventions and agent instructions |

## How to Use This Registry

When launching a sub-agent, the orchestrator:
1. Reads this registry once per session
2. Matches relevant skills by file context (extensions/paths the sub-agent will touch) AND task context (review, PR creation, testing, etc.)
3. Copies matching compact rule blocks into the sub-agent prompt as `## Project Standards (auto-resolved)`
4. Injects them BEFORE the task-specific instructions

Example injection:
```markdown
## Project Standards (auto-resolved)

### accessibility
- WCAG 2.2 compliance target: AA minimum
- All images MUST have alt text
- Color contrast: 4.5:1 for normal text
- ...

### python-patterns
- Readability first — clear names, obvious structure
- Type hints on ALL function signatures
- ...

## Task Instructions
[Original task here]
```
