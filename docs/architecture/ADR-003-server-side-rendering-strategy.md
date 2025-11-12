# ADR-003: Server-Side Rendering Strategy

**Status**: Accepted

**Date**: 2025-11-11

**Deciders**: Development team

## Context

The YouTube watch history analytics application needs to display data in a web browser. This requires choosing a rendering strategy: where HTML generation happens and how interactive features are implemented.

Key requirements:
- Display analytics data (tables, statistics, future visualizations)
- Simple deployment: must work on any system without complex build steps
- Self-hosted only: no CDN dependencies except for future D3.js visualizations
- Minimal dependencies: avoid Node.js ecosystem if possible
- Sufficient interactivity: form submissions, filtering, future chart interactions

Rendering strategy options:
- **Server-Side Rendering (SSR)**: Generate HTML on server, send complete pages
- **Single Page Application (SPA)**: Client-side rendering with React/Vue/etc
- **Hybrid**: Server-rendered initial load, client-side interactions

## Decision

Use **server-side rendering with Jinja2 templates** for all V1 features.

HTML is generated server-side and sent as complete pages. User interactions trigger full page reloads via standard HTTP GET/POST requests. No JavaScript build step required.

### Rationale

**SSR with Jinja2 chosen because**:
1. **Zero build step**: No npm, webpack, babel, or bundler required
2. **Simple deployment**: Python + HTML templates, runs anywhere
3. **No Node.js dependency**: Avoids "Node.js dependency hell" (project constraint)
4. **Sufficient for analytics**: Tables and forms work perfectly with SSR
5. **Flask native**: Jinja2 is Flask's built-in template engine
6. **Progressive enhancement**: Can add JavaScript later if needed (D3.js via CDN)
7. **Fast development**: Template syntax straightforward, no component lifecycle

**SPA (React/Vue) rejected because**:
- Requires Node.js toolchain (npm, webpack, babel)
- Complex build/deployment process
- Overkill for analytics dashboard with mostly static data
- Unnecessary learning curve for non-interactive tables
- Violates "minimal dependencies" and "simple deployment" constraints

**Hybrid approach rejected because**:
- Adds complexity without clear benefit
- Still requires JavaScript build tooling
- Analytics dashboard doesn't need SPA-level interactivity

### Implementation Pattern

**Template Structure**:
```
src/frontend/templates/
├── index.html      # Dataset overview
└── channels.html   # Top channels with filtering
```

**Template Features**:
- Jinja2 conditionals for empty states
- Form state preservation (selected values)
- Loop constructs for table rows
- Inline CSS (no external stylesheet dependencies)

**Interactivity via Forms**:
- HTML forms with GET method (bookmarkable URLs)
- Server processes query params, re-renders with new data
- Browser history and bookmarks work naturally

**Future JavaScript (D3.js)**:
- Load D3.js from CDN (no build step)
- Progressive enhancement: charts are additional feature
- Fallback: SSR tables remain functional without JavaScript

## Consequences

### Positive Consequences

- **Simple deployment**: Copy Python files + templates, run Flask server
- **No build step**: Edit template, refresh browser, see changes immediately
- **No Node.js required**: Single language stack (Python)
- **Browser compatibility**: Standard HTML works everywhere
- **Debugging simplicity**: View source shows actual HTML, no virtual DOM
- **Fast development**: No waiting for webpack rebuilds
- **Bookmarkable URLs**: Full page loads preserve state in URL
- **SEO-friendly**: Not relevant for localhost app, but demonstrates good practices

### Negative Consequences

- **Full page reloads**: Every interaction requires complete page refresh
  - Mitigated by: Fast queries (<1s on 58k dataset), acceptable UX for analytics dashboard
- **Limited interactivity**: No instant feedback, smooth animations, optimistic updates
  - Mitigated by: Analytics dashboard doesn't require high interactivity
  - Future: D3.js provides interactive visualizations where needed
- **No component reusability**: Templates don't compose like React components
  - Mitigated by: Small number of pages, limited duplication
  - Future: Jinja2 includes/macros if needed
- **Heavier bandwidth**: Full HTML page on each request vs JSON + client rendering
  - Mitigated by: Localhost deployment, bandwidth not a concern

### Neutral Consequences

- **Progressive enhancement path**: Can add JavaScript selectively without architecture change
- **Template testing**: Requires integration tests (Flask test client) vs unit testing components
- **State management**: URL query params instead of client-side state

## Notes

**Alternative considered**: React SPA with Flask API backend. Rejected because:
- Requires Node.js build toolchain (violates project constraints)
- Adds significant complexity: two development environments, API versioning, CORS
- No clear benefit for analytics dashboard use case
- Makes deployment significantly more complex

**D3.js integration** (deferred to Iteration 3):
- Will load from CDN: `<script src="https://d3js.org/d3.v7.min.js"></script>`
- No build step required, just include script tag
- SSR provides fallback tables if JavaScript disabled
- Demonstrates hybrid approach: SSR foundation + progressive JavaScript enhancement

**V2 considerations**:
- If real-time updates needed (unlikely for historical data), could add:
  - HTMX for partial page updates (still no build step)
  - WebSockets for live data (if YouTube API integration added)
- Current SSR choice doesn't prevent future enhancements
- Migration to SPA unlikely: project explicitly avoids Node.js complexity

**Development philosophy alignment**:
- "KISS Principle: Keep it simple, don't overcomplicate" (CLAUDE.md)
- "Minimal dependencies preferred" (CLAUDE.md)
- "Must be simple to set up on a different person's system" (CLAUDE.md)
- SSR with Jinja2 aligns perfectly with these constraints
