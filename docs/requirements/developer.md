# Developer Requirements

## Overview
Developer persona extends the system, writes tests, and debugs issues. Focus on fast feedback loops, clear separation of concerns, and maintainability.

## V1 - Core Development Experience

### Testing Infrastructure
- Test runner script to execute all tests at once
- Test data: curated real records safe for public display (committed to repo)
- Fast unit tests, reasonable integration test times

### Test Organization
```
tests/
├── unit/
│   ├── ingest/       # Per-component unit tests
│   ├── db/
│   ├── api/
│   └── frontend/
├── integration/      # Cross-component integration tests
└── e2e/              # End-to-end tests
```

### Test Isolation Strategy
- DB layer can run locally for integration tests
- "Known good state" setup method for tests
- Teardown deletes test databases
- Unit tests should be fast (no external dependencies)
- E2E tests run against full server deployment (V1 acceptable to be slower)

### Code Organization
Explicit separation of concerns:
```
src/
├── ingest/           # Data ingestion logic
├── db/               # Database layer
├── api/              # Backend API
└── frontend/         # Frontend/templates
```

### Development Mode
- Run server as foreground process (not daemonized)
- Drop into `pdb` on errors (`breakpoint()` enabled)
- Log statements dumped to stdout
- Enabled via `--debug` or `--dev` flag

### Code Documentation
- **Inline comments**: Where helpful, focus on "why" not "what"
- **Docstrings**: Focus on:
  - Why does this function exist?
  - What are the parameters useful for?
  - Not exhaustive API documentation, just enough context
- **Architecture Decision Records (ADRs)**: Capture key architectural decisions in `docs/architecture/`

### Code Formatting
- Black for automatic code formatting (default configuration)
- Black auto-formats all code (not just a checker)
- V1: Rely on developer discipline to run Black manually before commits
- No formatting checks in automated test suite

### Debugging Aids
- `--debug` flag enables:
  - `breakpoint()` statements active
  - Verbose SQL logging
  - Request/response logging
  - Stdout log output (instead of file)

## V2 - Enhanced Developer Experience

### Auto-Reload Development Server
- Server auto-reloads on code changes (Flask/FastAPI built-in support)
- Faster iteration during frontend/API development

### Automated Formatting Checks
- Optional: Add Black format checking to test script
- Optional: Pre-commit hooks for automatic formatting

## Deferred Decisions
- Detailed docstring conventions
- Test parallelization strategy
- Linting rules beyond Black

## Code Quality Philosophy
- "If it's not tested, it's not functional"
- Prefer mocking via inheritance for clear interfaces
- Assert-heavy, fail-fast approach
- Test doubles following inheritance pattern
- pytest framework throughout

## Onboarding Experience
- Developer should be able to:
  1. Clone repo
  2. Run dependency validation script
  3. Run test script successfully (using committed test data)
  4. Make a small change and see tests pass/fail appropriately
- No full 58k dataset required for basic development

## Design Constraints
- Keep setup simple (avoid complex toolchains)
- Minimal dependencies (portability over convenience)
- Clear error messages when things break
- Fast test execution for tight feedback loop
