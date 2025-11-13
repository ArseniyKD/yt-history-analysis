# ADR-006: Rewatch Tracking Definition and User Terminology

**Status**: Accepted

**Date**: 2025-11-12

**Deciders**: Development team

## Context

The application tracks video viewing patterns to provide engagement metrics. Users want to understand which videos and channels they rewatch, as this indicates content they find particularly valuable.

**Definition ambiguity**: Multiple ways to count "rewatches":
1. Count of unique videos watched 2+ times (e.g., video watched 3 times = 1 rewatch)
2. Total extra views beyond first view (e.g., video watched 3 times = 2 rewatches)
3. Total views of videos watched multiple times (e.g., video watched 3 times = 3 rewatches)

**Terminology challenge**: Internal code uses "rewatches" but this term is technical jargon. Need clear, user-friendly language for UI display.

**Scope**: Rewatch metrics appear throughout the application:
- Dataset overview (total rewatches)
- Global channel statistics (rewatches per channel)
- Per-year summaries (rewatches per year)
- Year-filtered channel views (rewatches per channel per year)

## Decision

**Rewatch definition**: Count of **unique videos watched 2+ times**
- A video watched once = 0 rewatches
- A video watched twice = 1 rewatch
- A video watched three times = 1 rewatch
- Rationale: Counts distinct videos with rewatch behavior, not total view count

**User-facing terminology**: "Videos Watched 2+ Times"
- Appears consistently in all UI displays (overview panels, table headers, summaries)
- Avoids technical jargon "rewatches"
- Makes the definition self-explanatory to end users

**Internal implementation**: Use term "rewatches" in code
- Function names: `get_total_rewatches()`, `get_channel_rewatches()`, `get_year_rewatches()`
- Database queries count `HAVING COUNT(*) > 1`
- No "rewatch" term exposed to users

## Consequences

### Positive Consequences

- **Clear metric definition**: Unambiguous counting method, easy to implement and test
- **Simple queries**: `SELECT COUNT(*) FROM (SELECT video_id ... HAVING COUNT(*) > 1)` pattern
- **User-friendly terminology**: Self-explanatory UI labels, no need for tooltips or help text
- **Consistent language**: Same terminology across all pages and contexts
- **Intuitive semantics**: Users understand "videos watched 2+ times" immediately

### Negative Consequences

- **Less granular than alternatives**: Doesn't distinguish between 2 views and 10 views of same video
  - Mitigated by: Metric still useful for identifying rewatch patterns
  - Future: Could add "most rewatched videos" view with view counts if needed
- **Code/UI terminology mismatch**: "rewatches" in code vs "Videos Watched 2+ Times" in UI
  - Mitigated by: Clear convention, documented in ADR
  - Trade-off: Clearer UI worth minor code/UI term divergence

### Neutral Consequences

- **Alternative metrics possible**: Could add total extra views, average views per rewatched video in future
- **Affects analytics layer design**: All rewatch functions follow same counting logic
- **Testing requires rewatch scenarios**: Test fixtures must include videos watched multiple times

## Notes

**Alternatives considered**:
1. **Total extra views**: More granular but confusing terminology ("2 rewatches" means watched 3 times?)
2. **Percentage of videos rewatched**: Less actionable than absolute counts
3. **Average rewatch rate**: Complex to explain, harder to understand at a glance

**Implementation pattern**: `_count_rewatches()` helper function with optional filters (channel, year) ensures consistent counting logic across all rewatch queries.

**Future enhancements**: Could add "Top Rewatched Videos" view showing individual videos with their view counts, complementing current channel-level aggregation.

**Related ADRs**: ADR-003 (Server-Side Rendering Strategy) - rewatch metrics displayed in SSR templates.
