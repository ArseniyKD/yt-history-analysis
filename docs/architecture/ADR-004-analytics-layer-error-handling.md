# ADR-004: Analytics Layer as Pure Library

**Status**: Accepted

**Date**: 2025-11-11

**Deciders**: Development team

## Context

The analytics layer (`src/analytics/queries.py`) contains query functions that retrieve and process data from the database. These functions need error handling and debugging support during development.

Error handling options:
- **Option A**: Analytics layer handles errors with `breakpoint()`
- **Option B**: Analytics layer raises exceptions, application layer handles errors
- **Option C**: Analytics layer returns error codes/tuples (e.g., `(data, error)`)

Development debugging requirements:
- Ability to drop into debugger on errors (using Python `breakpoint()`)
- Configurable via command-line flag (`--debug`)
- Only in development mode, not in operator's production usage

Initial plan (from `02-plan.md`) specified Option A:
```python
# Planned pattern (from plan document)
def get_top_channels(...):
    try:
        # ... query execution ...
    except Exception as e:
        logger.error(f"Query failed: {e}")
        breakpoint()  # In analytics layer
        raise
```

## Decision

Use **Option B**: Analytics layer raises exceptions, application layer conditionally calls `breakpoint()`.

Analytics functions are pure library code that:
- Log errors at ERROR level
- Raise exceptions without handling them
- Have no awareness of debug mode or breakpoints

Application layer (`src/api/app.py`) handles exceptions and debugging:
- Catches exceptions from analytics layer
- Calls `breakpoint()` conditionally based on `DEBUG_MODE` flag
- Re-raises exceptions after debugging

### Implementation Pattern

**Analytics Layer** (`src/analytics/queries.py`):
```python
def get_dataset_overview(db_conn: sqlite3.Connection) -> dict:
    """Pure query function."""
    try:
        # ... query execution ...
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise  # No breakpoint here
```

**Application Layer** (`src/api/app.py`):
```python
DEBUG_MODE = False  # Set by create_app() factory

@app.route('/')
def index():
    conn = get_db_connection()
    try:
        overview_data = queries.get_dataset_overview(conn)
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        if DEBUG_MODE:
            breakpoint()  # Conditional debugging
        conn.close()
        raise
    finally:
        conn.close()
```

### Rationale

**Option B chosen because**:
1. **Clean separation of concerns**: Analytics layer is pure data processing
2. **Reusability**: Analytics functions can be imported by scripts, CLIs, tests without unexpected debugger drops
3. **Testability**: Tests can catch and assert on exceptions without triggering debuggers
4. **Library pattern**: Analytics layer behaves like standard Python libraries (e.g., `sqlite3` raises exceptions)
5. **Configuration isolation**: Debug mode is application-level concern, not query-level

**Option A (original plan) rejected because**:
- Analytics functions would need awareness of execution context (debug mode)
- Tests would trigger breakpoints unless special test mode added
- Scripts using analytics functions would drop into debugger unexpectedly
- Violates single responsibility principle (queries shouldn't handle debugging)

**Option C (error codes) rejected because**:
- Unidiomatic Python (exceptions are standard error mechanism)
- Caller must check every result
- Harder to propagate errors up stack
- Loses exception context and stack traces

### Deviation from Original Plan

**Original plan** (from `docs/development-trace/2025-11-11-v1-end-user-iteration1/02-plan.md`):
- Task 3 & 4 specified `breakpoint()` in analytics layer exception handlers
- Task 8 specified `breakpoint()` in application layer exception handlers
- Both layers would have debugging logic

**Implemented pattern**:
- Analytics layer: pure exceptions, no breakpoints
- Application layer: conditional breakpoints based on `DEBUG_MODE`
- Single point of debug control

**Reason for deviation**:
- Discovered during implementation that analytics-level breakpoints interfere with testing
- Recognized analytics layer should be library-like (raise exceptions, no side effects)
- Improved separation of concerns and reusability

## Consequences

### Positive Consequences

- **Clean library interface**: Analytics functions are pure, predictable, testable
- **Flexible reuse**: Can import analytics queries in scripts, notebooks, CLIs safely
- **Better testing**: Tests catch exceptions normally without debugger interference
- **Single debug control point**: Only application layer needs debug flag awareness
- **Standard Python patterns**: Follows convention of library code raising exceptions
- **Simpler analytics code**: No conditional logic based on execution mode

### Negative Consequences

- **Slight code duplication**: Both layers have try/except blocks
  - Mitigated by: Duplication is minimal, pattern is clear and consistent
- **Two places for logging**: Error logged in both analytics and application layers
  - Mitigated by: Each log provides different context (query failure vs request failure)
- **Application layer must remember to handle**: Each route needs exception handling
  - Mitigated by: Small number of routes, pattern is straightforward

### Neutral Consequences

- **Exception propagation**: Exceptions flow naturally up the call stack
- **Stack traces preserved**: Full context available for debugging

## Notes

**Testing implications**:
- Analytics tests: Simple exception assertions (`pytest.raises`)
- API tests: Can test error handling behavior without triggering debuggers
- Debug mode tests: Can verify conditional breakpoint logic in application layer

**Future considerations**:
- If additional consumers of analytics layer added (CLI tools, batch scripts), they benefit from clean exception interface
- Could add custom exception types if specific error handling needed (e.g., `QueryTimeoutError`, `InvalidParameterError`)

**Alternative patterns considered**:
- Context managers for debug mode: Too complex for this use case
- Decorator for automatic debug handling: Adds indirection without clear benefit
- Global debug flag in analytics layer: Breaks library pattern, requires import-time configuration

**Development philosophy alignment**:
- "Exceptions for exceptional circumstances" (CLAUDE.md error handling patterns)
- "Testing philosophies for reliability-critical code" (clean exception testing)
- Clear separation of concerns (analytics = data, application = presentation + debugging)
