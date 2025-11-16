# ADR-007: Jinja2 Template Inheritance

**Status**: Accepted

**Date**: 2025-11-16

**Deciders**: Development team

## Context

After implementing 6 separate pages (index, channels, years, year_channels, temporal, month_views), significant duplication emerged across templates:
- Identical HTML boilerplate (doctype, head, meta tags)
- Duplicated navigation bar across all 6 pages
- Repeated footer structure with processing time
- CSS link repeated in every template

Duplication creates maintenance burden: adding a new nav item requires updating all 6 templates. As the application grows, this becomes increasingly error-prone.

Jinja2 provides template inheritance as a built-in feature, allowing templates to extend a base template and override specific sections via blocks.

## Decision

Implement **template inheritance using Jinja2 base template pattern**.

Create `base.html` containing common structure with defined blocks:
- `title`: Page-specific title
- `extra_head`: Optional additional head content (e.g., D3.js CDN)
- `heading`: Page-specific h1 heading
- `content`: Main page content
- `extra_scripts`: Optional scripts at end of body

All 6 templates converted to extend `base.html` and override only the blocks they need.

### Rationale

**Template inheritance chosen because**:
1. **Standard Flask/Jinja2 pattern**: Idiomatic approach, well-documented
2. **Eliminates duplication**: Nav bar now defined once in base.html
3. **Flexible block system**: Pages can add extra head content (D3.js) or scripts as needed
4. **Maintainable**: Single point of change for common structure
5. **Composable**: Child templates focus only on page-specific content
6. **Net reduction**: -73 lines of code after refactoring

**Alternative: Jinja2 includes/macros rejected because**:
- Less flexible for page-specific head content
- Requires explicit include statements in each template
- Doesn't eliminate boilerplate HTML structure duplication
- Base template pattern is more idiomatic for full page layout

**Alternative: Backend-generated nav structure rejected because**:
- Adds unnecessary backend complexity for static navigation
- Mixes presentation logic into application layer
- Template inheritance handles this elegantly

### Implementation Structure

```
src/frontend/templates/
├── base.html              # Base template with common structure
├── index.html             # extends base.html
├── channels.html          # extends base.html
├── years.html             # extends base.html
├── year_channels.html     # extends base.html
├── temporal.html          # extends base.html (uses extra_head, extra_scripts)
└── month_views.html       # extends base.html
```

**base.html blocks**:
```jinja2
{% block title %}YouTube Watch History{% endblock %}
{% block extra_head %}{% endblock %}
{% block heading %}YouTube Watch History{% endblock %}
{% block content %}{% endblock %}
{% block extra_scripts %}{% endblock %}
```

**Child template pattern**:
```jinja2
{% extends "base.html" %}
{% block title %}Page-Specific Title{% endblock %}
{% block heading %}Page-Specific Heading{% endblock %}
{% block content %}
  <!-- Page-specific HTML -->
{% endblock %}
```

**Special case (temporal.html)**:
Uses `extra_head` for D3.js CDN and `extra_scripts` for data loading:
```jinja2
{% block extra_head %}
<script src="https://d3js.org/d3.v7.min.js"></script>
{% endblock %}

{% block extra_scripts %}
<script>const monthlyData = {{ monthly_data | tojson }};</script>
<script src="{{ url_for('static', filename='temporal.js') }}"></script>
{% endblock %}
```

## Consequences

### Positive Consequences

- **Single source of truth**: Nav bar, footer, HTML boilerplate defined once
- **Easy to maintain**: Adding nav item requires one file change, not six
- **Cleaner child templates**: Focus only on page-specific content
- **Flexible blocks**: Pages can inject head content or scripts as needed
- **Standard pattern**: Follows Flask/Jinja2 best practices
- **Code reduction**: Net -73 lines across 7 files
- **Error prevention**: No risk of inconsistent nav bars or HTML structure

### Negative Consequences

- **Indirection**: Need to view base.html to see full page structure
  - Mitigated by: Standard pattern, well-understood by Flask developers
- **Block override complexity**: Must know which blocks exist
  - Mitigated by: Only 5 blocks, clearly named, documented in base.html
- **Harder to understand for non-Jinja2 developers**: Inheritance less obvious than plain HTML
  - Mitigated by: Standard web framework pattern, good documentation

### Neutral Consequences

- **Template testing unchanged**: Integration tests still verify full rendered pages
- **No impact on SSR strategy**: Still server-side rendering, just better organized
- **Future extensibility**: Easy to add more blocks if needed (e.g., `extra_meta` for SEO)

## Notes

**Refactoring approach**:
1. Created base.html with common structure
2. Converted templates one by one to extend base
3. Ran full test suite after each conversion (111 tests)
4. All tests passed without modification (purely structural refactor)

**Block naming rationale**:
- `extra_head`: "Extra" clarifies optional nature, "head" clarifies location
- `extra_scripts`: Parallel naming to extra_head, goes at end of body (standard practice)
- Other blocks (title, heading, content) are self-explanatory

**Future considerations**:
- Could add `extra_meta` block for page-specific meta tags (SEO, social media)
- Could add `breadcrumbs` block for hierarchical navigation
- Could extract reusable components as Jinja2 macros (e.g., data tables)

**Related ADRs**:
- ADR-003: Server-Side Rendering Strategy (base pattern aligns with SSR approach)
- ADR-008: D3.js Integration (temporal.html's extra_head/extra_scripts blocks enable D3.js)

**Development timeline**:
- Duplication tolerated through initial 4 pages (reasonable trade-off for velocity)
- Refactored after 6th page when duplication became maintenance burden
- Clean separation: feature commits first, refactoring commit separate
- Net result: Cleaner codebase ready for future pages
