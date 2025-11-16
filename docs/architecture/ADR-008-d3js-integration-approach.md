# ADR-008: D3.js Integration Approach

**Status**: Accepted

**Date**: 2025-11-16

**Deciders**: Development team

## Context

Iteration 3 introduced monthly temporal analysis requiring visualization of time-series data (8+ years of monthly view counts). SSR tables provide data accessibility, but visual representation improves user understanding of trends and patterns.

Key constraints:
- No build step (no npm, webpack, babel)
- No Node.js dependencies
- Simple deployment (must work on any system)
- Progressive enhancement (tables remain functional without JavaScript)
- Follows SSR-first approach (ADR-003)

D3.js chosen for visualization because:
- Available via CDN (no build step)
- Powerful for custom data visualizations
- Widely used, well-documented
- No framework dependencies

Architectural decisions needed:
1. Where to load D3.js from (CDN vs local copy)
2. Where to place visualization logic (inline vs separate file)
3. How to pass data from backend to frontend
4. Where to perform calculations (server vs client)
5. How to handle interactivity (tooltips, navigation)

## Decision

Implement **D3.js via CDN with separate static JavaScript file and client-side data handling**.

### Key Decisions

**1. D3.js Loading: CDN**
- Load from `https://d3js.org/d3.v7.min.js` in template head
- No local copy, no build step, no version management

**2. Visualization Logic: Separate Static File**
- Create `src/frontend/static/temporal.js` (234 lines)
- Load via `<script src="{{ url_for('static', filename='temporal.js') }}"></script>`
- Keep visualization logic out of template

**3. Data Passing: Global Variable**
- Backend passes JSON via Jinja template: `const monthlyData = {{ monthly_data | tojson }};`
- JavaScript reads global variable
- Simple, no AJAX, no API endpoint needed

**4. Client-Side Calculations**
- Yearly averages calculated in JavaScript from aggregated data
- Year grouping and color assignment done client-side
- Backend provides clean monthly aggregates, client handles visualization logic

**5. Interactivity: Event Handlers + Tooltips**
- Click on bar: Navigate to `/month-views?year=YYYY&month=MM`
- Hover on bar: Show tooltip with month + count
- Hover on average line: Show tooltip with year + average
- All handled client-side with D3.js event handlers

### Rationale

**CDN loading chosen over local copy because**:
- No manual version management or updates
- CDN provides caching and performance benefits
- Aligns with "minimal dependencies" constraint
- Consistent with project's acceptance of D3.js via CDN (ADR-003)

**Separate JS file chosen over inline <script> because**:
- Cleaner separation: template focuses on structure, JS file focuses on visualization
- Enables template inheritance (base.html) without complex inline script handling
- Easier to maintain and iterate on visualization logic
- Consistent with web development best practices
- Still no build step required (plain JavaScript file)

**Global variable data passing chosen over API endpoint because**:
- Simpler: No need for AJAX, fetch(), or async handling
- Data already available during SSR
- No additional HTTP request (better performance)
- Sufficient for static monthly aggregates
- Common pattern for SSR + client-side enhancement

**Client-side calculations chosen over backend pre-calculation because**:
- Simpler backend: Analytics layer returns clean monthly aggregates
- Yearly averages are presentation logic (belongs in frontend)
- Flexible: Easy to add more client-side computations (moving averages, etc.)
- Data volume small: 8 years * 12 months = 96 data points
- No performance concern for client-side grouping and averaging

**Alternative considered: Backend calculates yearly averages**
- Pros: More testable (Python unit tests)
- Cons: Mixes presentation logic into analytics layer, less flexible
- Decision: Current approach preferred for simplicity and separation of concerns

## Consequences

### Positive Consequences

- **No build step**: Edit JS file, refresh browser, see changes immediately
- **No Node.js required**: Plain JavaScript, D3.js via CDN
- **Clean separation**: Templates handle structure, JS handles visualization
- **Progressive enhancement**: Tables work without JavaScript, chart is additional feature
- **Simple deployment**: Just copy Python + templates + JS files
- **Flexible**: Easy to add more visualizations or modify existing ones
- **Testable backend**: Backend analytics layer tested with Python unit tests
- **Fast iteration**: No webpack rebuild, no transpilation, direct browser execution

### Negative Consequences

- **Manual testing required**: D3.js visualization tested manually in browser
  - Mitigated by: Acceptable per project guidelines (ADR-003)
  - Future: Consider Playwright or similar for visual regression tests in V2
- **Client-side calculation not unit tested**: Yearly averages calculated in JS
  - Mitigated by: Simple logic (group by year, sum/count), low risk
  - Mitigated by: Backend monthly aggregates thoroughly tested
  - Future: Consider Jest if client-side logic becomes complex
- **Global variable pattern**: Not ideal for large SPAs, but sufficient here
  - Mitigated by: Single global variable per page, small data volume
  - Not a concern for SSR-first application with limited JavaScript
- **CDN dependency**: Requires internet for initial D3.js load
  - Mitigated by: Browser caching after first load
  - Mitigated by: Could switch to local copy if needed (no code changes required)

### Neutral Consequences

- **Template inheritance enables this pattern**: `extra_head` and `extra_scripts` blocks make integration clean
- **Data flow**: Backend → Template → Global var → D3.js
- **Visualization-specific JS**: Each visualization page can have its own JS file if needed

## Notes

**Implementation details**:
```javascript
// Data passed from backend
const monthlyData = {{ monthly_data | tojson }};  // In template

// Client-side grouping and calculation
const yearlyData = {};
data.forEach(d => {
  const year = d.month.substring(0, 4);
  // ... group and calculate averages
});
```

**Visualization features implemented**:
- Horizontal bar chart (X-axis = counts at top, Y-axis = months grows down)
- Year-based color alternation (steelblue/skyblue)
- Yearly average overlay lines (vertical dashed red lines)
- Interactive tooltips (hover on bars and lines)
- Clickable bars (navigate to drill-down page)
- Legend (shows color meanings and average line)
- Dynamic SVG height based on data volume

**UX iterations during development**:
1. Line chart → Horizontal bar chart (better for many months)
2. Bottom X-axis → Top X-axis (timeline feel)
3. Dashed line hover issues → Invisible wider line overlay (better hover detection)
4. Single bar color → Year-based alternation (visual grouping)
5. Added yearly averages based on user feedback

**Testing approach**:
- Backend: Unit tests for monthly aggregation (9 new tests)
- Backend: Integration tests for temporal endpoint (3 new tests)
- Frontend: Manual verification in browser
  - Chart rendering and layout
  - Hover interactions and tooltips
  - Click navigation
  - Color alternation and legend
  - Empty database handling

**Future considerations**:
- **Responsive charts**: Make D3.js charts responsive to window resize
- **More visualizations**: Could add line charts, stacked bars, etc.
- **JavaScript testing**: Consider Jest or Playwright if client-side logic grows
- **Local D3.js copy**: If CDN dependency becomes concern, switch to local file
- **API endpoints**: If real-time updates needed, could add JSON endpoints

**Related ADRs**:
- ADR-003: Server-Side Rendering Strategy (defines SSR-first, progressive enhancement approach)
- ADR-007: Jinja2 Template Inheritance (provides extra_head/extra_scripts blocks for D3.js)

**Trade-off analysis**:

| Aspect | SSR Table | D3.js Visualization |
|--------|-----------|---------------------|
| Accessibility | Excellent | Good (table fallback) |
| Interactivity | None | High (hover, click) |
| Trend visibility | Poor | Excellent |
| Deployment | Simple | Simple (CDN) |
| Testing | Easy (integration) | Manual (browser) |
| Maintenance | Low | Medium |

Decision: Both approaches complement each other. Table provides accessibility and data export, D3.js provides visual insights and interactivity.

**Alignment with project philosophy**:
- "KISS Principle" (CLAUDE.md): D3.js via CDN is simplest approach
- "Minimal dependencies" (CLAUDE.md): No build tooling, just CDN + plain JS
- "Simple deployment" (CLAUDE.md): Copy files and run, no build step
- "Manual verification acceptable initially" (CLAUDE.md): Aligns with manual D3.js testing approach
