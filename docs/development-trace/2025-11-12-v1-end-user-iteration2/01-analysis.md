# Analysis: V1 End User Features - Iteration 2

**Date**: 2025-11-12
**Session**: v1-end-user-iteration2
**Scope**: Per-year filtering, navigation, rewatch tracking

## Context Review

**Iteration 1 Delivered** (branch merged to main):
- Dataset overview statistics (first/last view, total counts)
- Top channels view with configurable limit and deleted video toggle
- Analytics layer as pure library (`src/analytics/queries.py`)
- Flask app with SSR + Jinja2 (ADR-002, ADR-003)
- GET-based filtering with bookmarkable URLs (ADR-005)
- 59 tests passing in 0.21s
- Preview script for validation with production dataset (58k records)

**Established Patterns**:
- Multi-page architecture with focused routes
- Analytics functions raise exceptions, app layer handles debug mode (ADR-004)
- Query parameters encode view state
- Form state preservation in templates
- Test fixture: `analytics_sample.json` (292 records, 30 channels)

## Iteration 2 Scope

**From V1 Requirements** (`docs/requirements/end_user.md`):
1. Per-year metrics (total views, unique videos, unique channels per year)
2. Top channels per-year view
3. Navigation system with landing page
4. Rewatch tracking per channel

**Included in Iteration 2**:
- `/` becomes landing page with navigation links + dataset overview panel
- `/channels` stays as global channel data, add rewatch column
- New `/years` page: per-year summary table (one row per year)
- New `/year-channels` page: per-year channel data with year selector dropdown
- Rewatch counts added to all channel statistics
- Server processing time displayed on all pages
- Shared CSS file for consistent styling

**Deferred to Iteration 3**:
- Monthly temporal analysis (views per month+year)
- D3.js histogram visualizations
- Temporal patterns and trends

## Design Decisions

### Decision 1: Four-Page Architecture

**Page Structure**:

1. **`/` - Landing Page**
   - Dataset overview panel (first/last view dates, total views, unique videos/channels, total rewatches)
   - Navigation links to other pages

2. **`/channels` - Global Channel Data**
   - Existing functionality from Iteration 1 (top N channels, configurable limit, include deleted toggle)
   - Add rewatch count column

3. **`/years` - Per-Year Summary**
   - Table with one row per year
   - Stats: total views, unique videos, unique channels, rewatches, first/last view for that year

4. **`/year-channels` - Per-Year Channel Data**
   - Year selector dropdown
   - When year selected, shows top channels filtered to that year
   - Same columns as global channels page (views, unique videos, first/last view, rewatches)
   - Configurable limit and deleted video toggle (same as global page)

**Rationale**:
- Clear separation: global vs temporal views
- Landing page provides quick overview without navigation
- Dedicated per-year channel page avoids overloading global page with selectors
- Aligns with established multi-page pattern from Iteration 1

### Decision 2: Year Selector on Per-Year Channels Page

**Location**: `/year-channels` route

**Form Elements**:
- Year dropdown (populated with all years in dataset range)
- Limit dropdown (10, 20, 50, 100 - same as global page)
- Include deleted checkbox (same as global page)
- Submit button

**Query Parameters**: `?year=2023&limit=20&include_deleted=true`

**Default State**:
- If no year parameter: show most recent year's data
- Limit defaults to 10
- Include deleted defaults to false

**Rationale**:
- Separates per-year analysis from global analysis (cleaner UX than single page with toggles)
- Year dropdown makes temporal filtering explicit
- Reuses established filtering patterns (limit, deleted toggle) for consistency
- Query parameters enable bookmarking specific year views

### Decision 3: Year Range Calculation

**Approach**: Calculate year range from dataset first/last view dates

**Implementation**:
- Query min/max timestamps from database
- Extract years from those timestamps
- Generate year list: `range(min_year, max_year + 1)`
- Display all years in range, even if no data for specific year
- Show zero values or "No data" indicator for empty years

**Rationale**:
- Simpler than querying database for years with data
- Provides complete temporal picture (gaps visible)
- Year range unlikely to have many gaps in watch history dataset

### Decision 4: Rewatch Tracking

**Definition**: Video watched 2+ times by user

**Rewatch Count Meaning**: Sum of (views - 1) for each video with multiple views
- Example: Video watched 3 times = 2 rewatches

**Display Locations**:
- Landing page overview: total rewatches across all data
- Global channels page (`/channels`): rewatch count per channel column
- Per-year channels page (`/year-channels`): rewatch count per channel for selected year
- Years summary page (`/years`): rewatch count per year column

**Rationale**:
- First view is "watch", subsequent views are "rewatches"
- Provides engagement metric beyond raw view counts
- Answers "which channels do I rewatch most?" (global and per-year)

### Decision 5: Server Processing Time Display

**Implementation**:
- Timestamp at start of request handler
- Timestamp immediately before template render
- Calculate delta (processing time)
- Pass to template, display in page footer

**Format**: "Page generated in 0.123s" or similar

**Display Location**: Footer of all pages

**Rationale**:
- Provides performance visibility during development and preview
- Helps identify slow queries or bottlenecks
- Validates performance requirements (<1s page load target)
- Useful debugging tool for query optimization

### Decision 6: Shared CSS for Consistent Styling

**New File**: `src/frontend/static/style.css`

**Scope**:
- Common styles for all pages (typography, colors, spacing)
- Table styling (borders, padding, alternating rows)
- Form element styling (dropdowns, checkboxes, buttons)
- Layout patterns (header, footer, navigation links)
- Processing time footer styling

**Loading Pattern**: `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`

**Rationale**:
- Eliminates duplicated inline styles across templates
- Easier to maintain consistent look across 4 pages
- Standard Flask static file serving (no build step required)
- Iteration 1 used inline styles, but 4 pages justify external CSS

## Testing Strategy

**Test Fixture Verification**:
- Review `analytics_sample.json` for multi-year coverage and rewatch scenarios
- Enhance generator if needed to ensure 2-3 years of data with explicit rewatches
- Verify fixture includes edge cases: videos watched once vs multiple times

**New Test Coverage**:

**Unit Tests** (`tests/unit/analytics/test_queries.py`):
- Per-year summary stats function
- Rewatch calculation function
- Year-filtered channel stats function
- Edge cases: single-year dataset, no rewatches, empty year in range

**Integration Tests** (`tests/integration/api/test_endpoints.py`):
- `/` landing page with overview panel
- `/years` route
- `/year-channels` route with year parameter
- `/channels` route with rewatch column
- Year selector form submission on `/year-channels`
- Processing time present in rendered pages

**Testing Approach**: Same as Iteration 1 (in-memory SQLite, pytest, Flask test client)

## File Structure Changes

**New Files**:
- `src/frontend/static/style.css` - Shared stylesheet
- `src/frontend/templates/years.html` - Per-year summary page
- `src/frontend/templates/year_channels.html` - Per-year channel data page

**Modified Files**:
- `src/frontend/templates/index.html` - Add navigation + dataset overview panel
- `src/frontend/templates/channels.html` - Add rewatch column, apply CSS
- `src/analytics/queries.py` - Add per-year stats, rewatch calculation, year-filtered channel query functions
- `src/api/app.py` - Update `/`, add `/years` and `/year-channels` routes, add processing time calculation
- `tests/unit/analytics/test_queries.py` - Add tests for new query functions
- `tests/integration/api/test_endpoints.py` - Add tests for new routes and features

## Key Risks

**Risk 1: Year filtering performance**
- **Impact**: Medium (filtering on 58k records)
- **Likelihood**: Low (indexes support temporal queries)
- **Mitigation**: Test with production dataset during preview, measure with server processing time display; defer optimization to Iteration 4 if needed

**Risk 2: Rewatch query complexity**
- **Impact**: Medium (requires video-level grouping then channel-level aggregation)
- **Likelihood**: Low (established query patterns from Iteration 1)
- **Mitigation**: Test performance with processing time display, optimize if >1s

**Risk 3: Test fixture temporal coverage**
- **Impact**: Low (can regenerate fixture easily)
- **Mitigation**: Review fixture generation script, verify multi-year data with rewatches exists

## Success Criteria

- **4 pages functional**: `/` (landing + overview), `/channels`, `/years`, `/year-channels`
- **Year filtering works**: `/year-channels?year=2023` shows correct filtered data
- **Rewatch counts accurate**: Display correctly on all pages
- **All tests pass**: <1s execution time, increased coverage for new features
- **Manual verification**: Preview script with 58k dataset, all pages <1s load time
- **Processing time visible**: Displayed on all pages, provides performance feedback
- **Consistent styling**: CSS applied across all pages, visually consistent

## Notes

- Iteration 2 builds on proven patterns from Iteration 1
- No new technology or architectural changes needed
- Focus on incremental feature addition within established structure
- Per-year channel page provides temporal analysis without overloading global page
- Server processing time aids development and performance validation
- CSS file justified by 4-page count and styling consistency needs
