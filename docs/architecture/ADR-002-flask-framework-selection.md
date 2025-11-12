# ADR-002: Flask Framework Selection

**Status**: Accepted

**Date**: 2025-11-11

**Deciders**: Development team

## Context

V1 requires a web interface for YouTube watch history analytics. The application needs to serve HTML pages showing dataset statistics, top channels, and (in future iterations) temporal visualizations.

Key requirements:
- Self-hosted on localhost only (security constraint)
- Server-side rendering with Jinja2 templates
- Simple deployment: no complex build steps or infrastructure
- Sufficient for analytics dashboard with moderate traffic (single user)
- Python-based to leverage existing codebase
- Testing support (test client, fixtures)

Python web framework options considered:
- **Flask**: Micro-framework, mature ecosystem, Jinja2 integration
- **FastAPI**: Modern async framework with auto-generated OpenAPI docs
- **Django**: Full-featured MVC framework with ORM, admin interface
- **Bottle**: Minimal single-file framework
- **Pyramid**: Flexible but more complex configuration

## Decision

Use **Flask 3.0** as the web framework for V1.

### Rationale

**Flask chosen because**:
1. **Simplicity**: Minimal boilerplate for analytics dashboard use case
2. **Jinja2 native**: Built-in template engine, no additional integration needed
3. **Mature ecosystem**: Extensive documentation, well-understood patterns
4. **Testing support**: Flask test client provides excellent integration testing
5. **Familiarity**: Common framework, easier for future maintainers
6. **Sufficient features**: All needed capabilities without unnecessary complexity

**FastAPI rejected because**:
- Async capabilities unnecessary for this workload (SQLite is synchronous)
- OpenAPI documentation not needed (single-user, no API consumers)
- Adds learning curve without clear benefit

**Django rejected because**:
- Full MVC framework too heavyweight for analytics dashboard
- ORM not needed (direct SQLite with custom schema)
- Admin interface not required
- Adds significant complexity and dependencies

**Bottle/Pyramid rejected because**:
- Less mature ecosystems
- Fewer learning resources
- Flask provides better balance of simplicity and capabilities

### Implementation Pattern

Standard Flask factory pattern for testability:

```python
# Module-level app instance for decorator syntax
app = Flask(__name__, template_folder='../frontend/templates')

@app.route('/')
def index():
    # Route handlers
    pass

def create_app(db_path: str, debug: bool = False, verbose: bool = False):
    """Factory function for testing and configuration."""
    global DB_PATH
    DB_PATH = db_path
    # Configure logging, debug mode
    return app
```

## Consequences

### Positive Consequences

- **Fast development**: Minimal boilerplate gets features running quickly
- **Easy testing**: Flask test client integrates seamlessly with pytest
- **Simple deployment**: Single Python process, no build step required
- **Template integration**: Jinja2 works natively, no adapter layer
- **Good documentation**: Extensive resources for troubleshooting
- **Standards compliance**: Uses WSGI standard, portable to production servers if needed

### Negative Consequences

- **No async support**: Cannot leverage async/await patterns if needed in future
  - Mitigated by: SQLite is synchronous anyway, async not beneficial for this use case
- **Manual API documentation**: No auto-generated docs like FastAPI
  - Mitigated by: Single-user app, no API consumers, docs not needed
- **Less opinionated**: More choices to make about project structure
  - Mitigated by: Simple app structure, patterns established in V1

### Neutral Consequences

- **WSGI vs ASGI**: Flask uses WSGI (synchronous), not ASGI (async)
  - Not an issue for current requirements
- **Extension ecosystem**: Flask extensions available but not required for V1

## Notes

**Alternative considered**: FastAPI for modern async patterns and auto-docs. Rejected because:
- Async provides no benefit for synchronous SQLite operations
- Auto-generated OpenAPI docs unnecessary for single-user analytics dashboard
- Adds learning complexity without clear value

**V2 considerations**:
- If API integration needed (YouTube API calls), Flask-SQLAlchemy and Flask-RESTful could be added
- Current choice doesn't constrain future capabilities
- Could migrate to FastAPI in V3 if async operations become necessary, but unlikely

**Development experience alignment**:
- User has web development knowledge gaps (documented in CLAUDE.md)
- Flask's simplicity reduces learning curve
- Standard patterns make code review more educational
