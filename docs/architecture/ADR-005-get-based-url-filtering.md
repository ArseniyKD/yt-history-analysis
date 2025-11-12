# ADR-005: GET-Based URL Query Parameters for Filtering

**Status**: Accepted

**Date**: 2025-11-11

**Deciders**: Development team

## Context

The web interface needs to allow users to configure how data is displayed:
- Top channels page: number of channels to show (10, 20, 50, 100)
- Top channels page: whether to include deleted/private videos

These configuration options filter/modify the view but don't change underlying data. Users should be able to:
- Adjust settings and see updated results
- Potentially bookmark or share specific views
- Use browser back/forward buttons naturally

HTTP method options:
- **GET with query parameters**: `GET /channels?limit=20&include_deleted=true`
- **POST with form data**: `POST /channels` with form body
- **Client-side only**: JavaScript updates without server round-trip

State preservation options:
- **Query parameters in URL**: State encoded in URL
- **Session storage**: State stored server-side, referenced by session ID
- **Cookies**: State stored in browser cookies

## Decision

Use **HTTP GET requests with query parameters** for all filtering and display configuration.

Configuration state is encoded in URL query parameters:
- `limit=20` - Number of channels to display
- `include_deleted=true` - Whether to include deleted videos

HTML forms use `method="GET"` to submit configuration changes.

### Implementation Pattern

**Route Handler**:
```python
@app.route('/channels', methods=['GET'])
def channels():
    # Parse query parameters
    limit = int(request.args.get('limit', 10))
    limit = max(1, min(limit, 1000))  # Bounds check

    include_deleted_param = request.args.get('include_deleted', 'false').lower()
    include_deleted = include_deleted_param == 'true'

    # Execute query with parameters
    top_channels = queries.get_top_channels(conn, limit, include_deleted)

    # Render with current state for form preservation
    return render_template('channels.html',
                          channels=top_channels,
                          current_limit=limit,
                          include_deleted=include_deleted)
```

**HTML Form**:
```html
<form method="GET" action="/channels">
    <select name="limit">
        <option value="10" {% if current_limit == 10 %}selected{% endif %}>10</option>
        <option value="20" {% if current_limit == 20 %}selected{% endif %}>20</option>
    </select>

    <input type="checkbox" name="include_deleted" value="true"
           {% if include_deleted %}checked{% endif %}>

    <button type="submit">Update</button>
</form>
```

### Rationale

**GET with query parameters chosen because**:

1. **Semantic correctness**: GET is for retrieving resources, not modifying data
   - REST principle: GET requests are safe and idempotent
   - Filtering/configuring views retrieves data, doesn't change it

2. **Bookmarkable URLs**: Users can save specific views
   - Example: `http://localhost:8000/channels?limit=50&include_deleted=true`
   - Copy/paste URL preserves exact view configuration
   - Useful for referring back to specific analyses

3. **Browser history**: Back/forward buttons work naturally
   - Each configuration change creates history entry
   - Users can navigate through different views easily

4. **Shareable**: URLs can be shared between users (if multiple analysts in future)
   - Not critical for single-user V1, but good practice

5. **No server-side state**: Stateless requests, easier to reason about
   - Each request is independent
   - No session cleanup needed
   - Simpler error recovery (just reload)

6. **Standard web patterns**: Follows established conventions
   - Search engines use GET for query params
   - Analytics dashboards typically use GET for filters
   - Familiar pattern for maintainers

**POST rejected because**:
- Semantically incorrect for read-only operations
- No bookmarking capability
- Browser back button requires form resubmission warning
- More complex state management
- CSRF protection needed (unnecessary complexity for localhost)

**Client-side only (JavaScript) rejected because**:
- Requires JavaScript (violates progressive enhancement)
- State lost on page reload unless URL updated anyway
- Adds complexity without clear benefit for this use case
- SSR architecture chosen (ADR-003) makes client-side state awkward

**Session storage rejected because**:
- Requires server-side session management
- State not preserved in URL (breaks bookmarking)
- More complex with stateless REST principles
- Unnecessary for simple filtering parameters

### Parameter Design Choices

**Limit parameter**:
- Values: 10, 20, 50, 100
- Default: 10
- Validation: `max(1, min(limit, 1000))` prevents absurd values
- Rationale: Preset values in dropdown prevent invalid inputs

**Include deleted parameter**:
- Type: Boolean
- Encoding: `include_deleted=true` when checkbox checked, absent when unchecked
- Default: false (when parameter absent)
- Parsing: `request.args.get('include_deleted', 'false').lower() == 'true'`
- Rationale: Standard HTML checkbox behavior

## Consequences

### Positive Consequences

- **Bookmarkable views**: Users can save URLs to specific configurations
- **Browser integration**: Back/forward buttons work intuitively
- **Stateless server**: No session management complexity
- **REST compliance**: Proper HTTP method semantics
- **URL as state**: Complete state visible in address bar
- **No CSRF concerns**: GET requests don't require CSRF tokens
- **Simple testing**: Integration tests just construct URLs with query params
- **Debugging ease**: State visible in browser address bar, logs, network tab

### Negative Consequences

- **URL length limits**: Complex queries could hit browser URL length limits
  - Mitigated by: Simple parameters, well under 2000 character practical limit
- **Parameter pollution**: Multiple parameters can make URLs messy
  - Mitigated by: Only 2 parameters, both optional, reasonable defaults
- **No POST advantages**: Cannot use POST-specific features
  - Not a problem: Don't need request body, file uploads, or large payloads

### Neutral Consequences

- **URL visibility**: Configuration visible in address bar (not a concern for localhost)
- **Browser history growth**: Each filter change creates history entry (expected behavior)
- **Query parameter encoding**: Standard URL encoding handles special characters

## Notes

**Alternative considered**: POST with redirect to GET (PRG pattern). Rejected because:
- Adds unnecessary complexity (two requests per interaction)
- Benefits of PRG (preventing duplicate form submissions) not relevant for read-only operations
- GET directly achieves same result with simpler flow

**Form state preservation**:
- Server passes `current_limit` and `include_deleted` back to template
- Template uses these to set `selected` attribute on dropdown, `checked` on checkbox
- User sees current configuration reflected in form controls
- Provides clear feedback on active filters

**Testing benefits**:
```python
def test_channels_custom_limit(client):
    response = client.get('/channels?limit=20')
    assert response.status_code == 200
    # Verify limit respected
```
No need to construct POST bodies, handle CSRF, or manage sessions.

**Future considerations**:
- Additional filters (date ranges, channel name search) can be added as new query parameters
- If parameters become numerous (>5-6), consider:
  - Single "filter" object in query string (JSON encoded)
  - Client-side state management with URL sync
- Current design scales to ~5-10 parameters comfortably

**Web development pattern alignment**:
- Standard REST principles (GET for reads)
- Common in analytics/BI tools (Grafana, Metabase, etc.)
- Aligns with stateless architecture
- Educational value: demonstrates proper HTTP semantics for code review

**Development philosophy alignment**:
- "KISS Principle: Keep it simple" (CLAUDE.md) - simplest solution that works
- Standard patterns make code more maintainable
- No unnecessary abstraction or premature optimization
