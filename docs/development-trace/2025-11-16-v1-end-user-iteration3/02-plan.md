# Plan: V1 End User Features - Iteration 3

**Date**: 2025-11-16
**Session**: v1-end-user-iteration3
**Scope**: Monthly temporal analysis with D3.js visualizations + drill-down

## Reference Documents

- [Analysis](docs/development-trace/2025-11-16-v1-end-user-iteration3/01-analysis.md)
- [End User Requirements](docs/requirements/end_user.md)
- [Architecture](docs/architecture.md)

## Implementation Strategy

**Small commits**: Each task = one commit with code + tests
**Session boundaries**: Marked with `[SESSION BREAK]` for context compaction
**Testing**: Unit tests for queries, integration tests for endpoints, manual verification for D3.js
**Navigation**: Drill-down and temporal are separate nav-bar entries, bar chart remains clickable

## Task Breakdown

### Phase 1: Backend - Monthly Analytics Layer

**Task 1: Monthly aggregation query**
- Add `get_monthly_view_counts()` to analytics layer
- Returns list of (year-month, count) tuples in reverse chronological order
- Unit tests: verify grouping, sorting, empty dataset handling
- **Commit**: "Add monthly view aggregation to analytics layer"

**Task 2: Dataset year range query**
- Add `get_dataset_year_range()` to analytics layer
- Returns (min_year, max_year) tuple based on timestamp data
- Reuses existing latest timestamp logic from `app.py`
- Unit tests: verify range calculation, empty dataset handling
- **Commit**: "Add dataset year range query to analytics layer"

**Task 3: Month drill-down query**
- Add `get_videos_for_month(year, month)` to analytics layer (separate year/month parameters)
- Returns videos watched in specified month with timestamp, title, channel
- Unit tests: verify filtering, chronological order, invalid month handling
- **Commit**: "Add month drill-down query to analytics layer"

### Phase 2: Backend - Endpoints

**Task 4: Temporal overview endpoint**
- Add `/temporal` route in Flask app
- Calls `get_monthly_view_counts()`, passes data to template
- Integration test: verify response status, data structure, processing time footer
- **Commit**: "Add /temporal endpoint for monthly overview"

**Task 5: Month drill-down endpoint**
- Add `/month-videos` route with `?year=YYYY&month=MM` parameters
- Validates year (in dataset range) and month (1-12)
- Defaults to latest month (using existing latest timestamp) if invalid/out-of-range
- Integration tests: valid parameters, invalid format, missing parameters, out-of-range defaults
- **Commit**: "Add /month-videos endpoint with dropdown parameters"

**[SESSION BREAK]** - Backend complete, can start fresh session for frontend

### Phase 3: Frontend - Templates

**Task 6: Temporal overview template**
- Create `templates/temporal.html` with nav-bar (including both new pages), chart container (empty SVG), data table
- Table displays all months + counts, includes jump-to-table button
- Manual test: verify table renders, navigation works
- **Commit**: "Add temporal.html template with chart placeholder"

**Task 7: Month drill-down template**
- Create `templates/month-videos.html` with nav-bar (duplicated), page title, dropdown form, video table
- Form: year dropdown (constrained to dataset range), month dropdown (1-12), submit button
- Table columns: timestamp, video title, channel name
- Manual test: verify dropdowns populate, form submits, table layout
- **Commit**: "Add month-videos.html template with dropdown form"

**Task 8: Update existing templates with new nav-bar entries**
- Add "Monthly Trends" and "Month Videos" links to nav-bar in all existing templates
- Manual test: verify links appear on all pages, redirect correctly
- **Commit**: "Add new pages to navigation in existing templates"

**[SESSION BREAK]** - Templates ready, can focus on D3.js in isolation

### Phase 4: Frontend - D3.js Visualization

**Task 9: D3.js chart integration**
- Add D3.js CDN link to `templates/temporal.html`
- Implement horizontal bar chart in `<script>` tag: Y-axis (year-month), X-axis (view count)
- Add tooltips on hover, click handler for bar → redirect to `/month-videos?year=YYYY&month=MM`
- Manual test: verify chart renders, tooltips work, clicks navigate correctly with pre-selected month
- **Commit**: "Add D3.js horizontal bar chart with click navigation"

### Phase 5: Navigation Refactoring

**Task 10: Centralize nav-bar generation**
- Create nav-bar data structure in `app.py` (list of nav entries)
- Pass nav-bar data to all templates via Jinja context
- Update all templates to generate nav-bar from context (replace duplicated HTML)
- Integration tests: verify all pages render with correct nav-bar
- **Commit**: "Refactor nav-bar to central generation"

## Testing Summary

**Unit tests (pytest)**:
- Monthly aggregation logic (grouping, sorting)
- Dataset year range calculation
- Month drill-down filtering (valid/invalid months, year range)
- Date formatting edge cases

**Integration tests (pytest)**:
- `/temporal` endpoint response structure
- `/month-videos` endpoint with various parameter combinations
- Default behavior for invalid/out-of-range parameters
- Nav-bar rendering across all pages

**Manual tests**:
- D3.js chart rendering with production dataset (58k records)
- Tooltip display on hover
- Click navigation from bar chart to drill-down page
- Dropdown form submission and month selection
- Browser back button navigation
- Page load performance (<1s requirement)

## Session Break Rationale

**Break 1 (after Task 5)**: Backend queries and endpoints are testable independently. Frontend can start fresh with working API.

**Break 2 (after Task 8)**: Templates provide structure for D3.js work. D3.js integration can be focused session without backend context.

## Success Criteria

- All 10 commits build and pass tests
- `/temporal` shows clickable bar chart + data table
- `/month-videos` has year/month dropdowns with dataset-constrained year range
- Invalid/out-of-range parameters default to latest month
- Both pages accessible via nav-bar, bar chart click also navigates
- Nav-bar centrally generated (single source of truth)
- Both pages load in <1s with 58k records
- V1 temporal requirements complete (views per month+year, histogram visualization)

## Changes from Original Analysis

- **Drill-down interaction**: Dropdown form instead of query parameter only
- **Navigation**: Both pages in nav-bar (not just temporal)
- **URL structure**: `?year=YYYY&month=MM` instead of `?month=YYYY-MM`
- **Default behavior**: Uses existing latest timestamp from app.py
- **Nav-bar refactoring**: Added as final phase for DRY principle
