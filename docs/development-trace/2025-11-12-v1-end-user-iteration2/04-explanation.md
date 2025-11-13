# Explanation: V1 End User Features - Iteration 2

**Date**: 2025-11-12
**Session**: v1-end-user-iteration2

## Key Technical Decisions

### 1. Rewatch Definition
**Decision**: Count unique videos watched 2+ times (not total extra views)
**Rationale**: Simpler metric, easier queries, sufficient for engagement patterns
**User terminology**: "Videos Watched 2+ Times" (not "rewatches")
**Documented**: ADR-006

### 2. Year Selector Defaults
**Decision**: Default to most recent year, validate range, fall back gracefully
**Rationale**: Better UX, sensible default, maintains bookmarkable URLs
**Implementation**: Get range from `get_dataset_date_range()`, build dropdown dynamically

### 3. Navigation Structure
**Decision**: All 4 pages as peers in navigation bar, no "back" links
**Rationale**: Pages show different analyses not hierarchy, consistent navigation
**Updated**: ADR-003 with page creation strategy

### 4. Expression Index Optimization
**Problem**: Year queries 4-10x slower (0.220s vs 0.04s)
**Solution**: Add `idx_views_year` on `strftime('%Y', timestamp)`
**Trade-off**: +76ms ingest (+6.5%) vs 4.4x query speedup (0.220s → 0.050s)
**Decision**: Query performance prioritized for interactive app

### 5. Processing Time Display
**Decision**: Add footer to all pages showing generation time
**Rationale**: Performance visibility, identified optimization opportunity

## Implementation Patterns

**Year Range**: Calculate from min/max timestamps, show all years in range (gaps visible)
**Rewatch Counting**: Single `_count_rewatches()` helper with optional filters
**Processing Time**: Measure start to render, display in template footer

## Testing

**Unit**: Analytics functions with in-memory SQLite
**Integration**: Flask test client, 13 new tests (89 total)
**Manual**: Validated with production dataset (58k records)

## Performance

**Queries** (with index): All pages <0.1s
**Ingest**: 1.244s (+76ms from baseline)

## Documentation

**ADRs**: Created ADR-006 (rewatch definition), updated ADR-003 (page strategy)
**Dev traces**: Analysis, plan, execute, explanation phases complete
