# Plan: V1 End User Features - Iteration 2

**Date**: 2025-11-12
**Session**: v1-end-user-iteration2
**Scope**: Per-year filtering, navigation, rewatch tracking

## Overview

This plan implements per-year filtering, navigation, rewatch tracking, and performance monitoring across a 4-page architecture. Work proceeds in three phases with natural context compaction points.

---

## Phase 1: Analytics Layer Foundation

**Scope**: Extend analytics layer with rewatch tracking, per-year statistics, and year-filtered channel queries. All new functions follow established patterns from Iteration 1 (pure functions raising exceptions, app layer handles debug mode).

**Tasks**:

1. **Review and enhance test fixture** (`analytics_sample.json`)
   - Verify multi-year coverage (2-3 years minimum)
   - Ensure rewatch scenarios exist (videos watched 2+ times)
   - Regenerate if needed using existing generator script
   - Document fixture characteristics for test design

2. **Rewatch calculation queries**
   - Add function to calculate total rewatches across dataset (for landing page overview)
   - Add rewatch count per channel (for global channels page)
   - Add rewatch count per channel per year (for year-filtered channels page)
   - Add rewatch count per year (for years summary page)
   - Unit tests covering: no rewatches, single rewatch, multiple rewatches, edge cases

3. **Per-year summary statistics**
   - Add function returning list of year summaries (one dict per year in dataset range)
   - Each year: total views, unique videos, unique channels, rewatches, first/last view timestamp for that year
   - Calculate year range from dataset min/max timestamps
   - Unit tests covering: single year, multi-year, gaps in years, empty dataset

4. **Year-filtered channel statistics**
   - Add function taking year parameter, returns top channels for that year
   - Same structure as global channel stats but filtered to specific year
   - Supports limit, include_deleted, rewatch count
   - Unit tests covering: valid year, year with no data, year outside range

5. **Run Black on changed files**

**Commit Point 1**: After analytics layer complete with all tests passing
- Commit message: "Add per-year and rewatch analytics functions"
- ~3-4 new functions in `queries.py`, ~50-100 new test lines

**Context Compaction Point**: After Phase 1 complete
- Analytics foundation is stable and tested
- Can restart execution from "build frontend on top of analytics API"
- Reduces context by ~40% (implementation details of analytics queries not needed for frontend work)

---

## Phase 2: Frontend Structure and Styling

**Scope**: Create CSS file, update landing page with navigation, apply styling consistently. This establishes visual foundation before adding new pages.

**Tasks**:

6. **Shared CSS file**
   - Create `src/frontend/static/style.css`
   - Define styles for: typography, tables, forms, navigation, layout, footer
   - Consistent look: borders, spacing, colors, alternating table rows
   - Processing time footer styling

7. **Landing page update**
   - Modify `/` route to call dataset overview query (enhanced with total rewatches)
   - Update `index.html` template with navigation links to all 4 pages
   - Add dataset overview panel: first/last view, total views/videos/channels/rewatches
   - Apply CSS styling, link stylesheet
   - Integration tests: verify overview stats present, navigation links functional

8. **Global channels page update**
   - Modify `/channels` route to include rewatch counts in channel data
   - Update `channels.html` template to add rewatch column
   - Preserve existing functionality: limit, include_deleted, form state
   - Apply CSS styling
   - Integration tests: verify rewatch column present, values correct

9. **Run Black on changed files**

**Commit Point 2**: After landing page and global channels updated
- Commit message: "Add shared CSS and update landing/channels pages with rewatch tracking"
- CSS file + 2 template updates + route updates + tests

**Context Compaction Point**: After Phase 2 complete
- Visual style established, navigation structure in place
- Can restart from "add two new pages using established patterns"
- Reduces context by ~30% (CSS details and navigation implementation not needed for new pages)

---

## Phase 3: New Pages and Performance Monitoring

**Scope**: Add per-year summary page and per-year channels page. Add server processing time display to all pages. Final validation.

**Tasks**:

10. **Per-year summary page**
    - Add `/years` route calling per-year summary analytics function
    - Create `years.html` template: table with one row per year
    - Columns: year, total views, unique videos, unique channels, rewatches, first/last view
    - Apply CSS styling
    - Integration tests: verify route returns 200, all years present, stats correct

11. **Per-year channels page**
    - Add `/year-channels` route with year/limit/include_deleted query parameters
    - Default: most recent year if no year parameter provided
    - Create `year_channels.html` template: year selector dropdown + channel table
    - Year dropdown populated from dataset year range
    - Form elements: year, limit (10/20/50/100), include_deleted checkbox
    - Apply CSS styling
    - Integration tests: verify route with/without year param, form submission, data filtering

12. **Add server processing time display**
    - Add timing logic to all route handlers: timestamp at start, timestamp before render, calculate delta
    - Pass processing time to all templates
    - Update all templates to display processing time in footer
    - Integration tests: verify processing time present in rendered HTML

13. **Run Black on changed files**

**Commit Point 3**: After new pages and processing time complete
- Commit message: "Add per-year pages and server processing time display"
- 2 new routes + 2 new templates + timing logic + tests

---

## Phase 4: Validation

**Tasks**:

14. **Full test suite verification**
    - Run `pytest tests/ -v`
    - Verify all tests pass, execution time <1s
    - Check coverage for new functionality
    - Address any failures

15. **Manual validation with production dataset**
    - Use preview script with 58k record dataset
    - Verify all 4 pages load successfully
    - Check processing time <1s per page
    - Verify rewatch counts look reasonable
    - Test year selector with multiple years
    - Verify bookmarkable URLs work correctly

**Commit Point 4**: After validation complete and any fixes applied
- Run Black on changed files (if fixes needed)
- Commit message: "Fix validation issues" (if any fixes needed)
- Otherwise, no commit needed

---

## Commit Strategy Summary

**Commit 1** (After Phase 1):
- Analytics layer implementation + tests
- Run Black on changed files
- Commit message: "Add per-year and rewatch analytics functions"

**Commit 2** (After Phase 2):
- CSS file + landing/channels page updates + tests
- Run Black on changed files
- Commit message: "Add shared CSS and update landing/channels pages with rewatch tracking"

**Commit 3** (After Phase 3):
- New pages + processing time + tests
- Run Black on changed files
- Commit message: "Add per-year pages and server processing time display"

**Commit 4** (After Phase 4, if needed):
- Any validation fixes
- Run Black on changed files
- Commit message: "Fix validation issues"

Each commit includes working code + passing tests, main branch stays green.

---

## Context Compaction Points

1. **After Phase 1**: Analytics API complete, frontend work begins fresh
2. **After Phase 2**: Styling/navigation complete, new pages follow pattern
3. **After Phase 3**: All implementation done, only validation remains

At each point, you can save session state and restart execution with high-level summary of completed work.

---

## Risk Mitigation

- **Performance risk**: Addressed by processing time display, measured during manual validation
- **Test fixture risk**: Addressed by fixture review as first task
- **Rewatch query complexity**: Mitigated by unit tests before integration, same patterns as Iteration 1

---

## Dependencies

- Phase 2 depends on Phase 1 (analytics functions must exist)
- Phase 3 depends on Phase 2 (CSS file must exist for new templates)
- Phase 4 depends on Phase 3 (all pages must exist for validation)

Within phases, tasks can sometimes proceed in parallel (e.g., tasks 2-4 in Phase 1 are independent once fixture is ready).

---

## Success Criteria

- **4 pages functional**: `/` (landing + overview), `/channels`, `/years`, `/year-channels`
- **Year filtering works**: `/year-channels?year=2023` shows correct filtered data
- **Rewatch counts accurate**: Display correctly on all pages
- **All tests pass**: <1s execution time, increased coverage for new features
- **Manual verification**: Preview script with 58k dataset, all pages <1s load time
- **Processing time visible**: Displayed on all pages, provides performance feedback
- **Consistent styling**: CSS applied across all pages, visually consistent
