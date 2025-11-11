# ADR-001: Database Schema Design for V1

**Status**: Accepted

**Date**: 2025-11-11

**Deciders**: Development team

## Context

YouTube watch history analysis requires storing ~58k view records with associated video and channel information. The primary use case for V1 is channel-centric analytics: views per channel, temporal analysis by channel, top channels, etc.

Key constraints:
- Read-optimized for analytics queries (V1 has no write operations beyond initial ingest)
- Immutable data (YouTube history doesn't change after export)
- Need to preserve temporal granularity for future features
- Some videos lack channel info (deleted/private videos)
- YouTube URLs may change format, but IDs are stable

Initial design considerations included:
- **Option A (Normalized)**: Separate channels, videos, and views tables with full temporal data
- **Option B (Denormalized)**: Aggregate view counts in videos table, lose per-view timestamps

## Decision

Implement a hybrid normalized schema with strategic denormalization:

```sql
channels:
  - channel_id (TEXT PRIMARY KEY)
  - channel_name (TEXT NOT NULL)

videos:
  - video_id (TEXT PRIMARY KEY)
  - title (TEXT NOT NULL)
  - channel_id (TEXT NOT NULL, FK to channels)

views:
  - view_id (INTEGER PRIMARY KEY AUTOINCREMENT)
  - video_id (TEXT NOT NULL, FK to videos)
  - channel_id (TEXT NOT NULL, FK to channels)  -- DENORMALIZED
  - timestamp (TEXT NOT NULL)  -- ISO8601 format
```

### Key Design Choices

1. **Denormalize channel_id in views table**
   - Redundant with videos.channel_id, but eliminates JOIN for channel-centric queries
   - Trade-off: Redundant storage vs query performance
   - Justified by: Read-heavy analytics workload, immutable data (no update anomalies)

2. **Store IDs only, not URLs**
   - Reconstruct URLs on demand: `https://www.youtube.com/watch?v={video_id}`
   - Immune to YouTube URL format changes
   - Smaller database size

3. **Sentinel value for missing channels**
   - Use `'NO_CHANNEL'` instead of NULL for deleted/private videos
   - Avoids null handling throughout codebase
   - Enables simple queries: `WHERE channel_id = 'NO_CHANNEL'`
   - Follows systems pattern (like -1 for invalid file descriptor)

4. **Preserve full temporal granularity**
   - Store every view with timestamp (not just aggregates)
   - Enables future video-level drill-down without migration
   - Trade-off: Larger views table vs flexibility

5. **Strip action prefixes from titles**
   - Remove "Watched " and "Viewed " prefixes during ingest
   - Store actual content titles, not UI metadata

### Indexes

```sql
CREATE INDEX idx_views_channel ON views(channel_id);
CREATE INDEX idx_views_channel_timestamp ON views(channel_id, timestamp);
CREATE INDEX idx_views_timestamp ON views(timestamp);
```

**Rationale**:
- `idx_views_channel`: Aggregate queries without temporal filtering (e.g., total views per channel)
- `idx_views_channel_timestamp`: Temporal analysis per channel (e.g., views per channel per year)
- `idx_views_timestamp`: Global temporal queries (e.g., views per month across all channels)

## Consequences

### Positive Consequences

- **Fast channel-centric queries**: No JOINs needed for primary V1 analytics
- **Optimized aggregations**: Index supports both aggregated and temporal queries
- **Future-proof**: Preserves temporal data for V2 features without migration
- **Simple null handling**: Sentinel value eliminates special cases
- **URL stability**: ID-based storage immune to YouTube format changes
- **Smaller footprint**: No redundant URL storage

### Negative Consequences

- **Redundant channel_id**: ~58k redundant TEXT fields in views table
  - Mitigated by: SQLite compression, cheap storage, read optimization priority
- **JOIN for video details**: Video title lookups require join to videos table
  - Mitigated by: V1 doesn't display video titles in main views
- **Sentinel filtering**: Must exclude 'NO_CHANNEL' from "top channels" queries
  - Mitigated by: Simple WHERE clause, no complex logic
- **Three indexes on views**: Additional storage and insert overhead
  - Mitigated by: Ingest is one-time operation, read performance is critical

### Neutral Consequences

- **Read-optimized design**: Write performance not a concern for this use case
- **No URL validation**: Trust YouTube export data structure

## Notes

**Alternative considered**: Store URLs and derive IDs on demand. Rejected because:
- IDs are more stable than URL formats
- Parsing overhead on every query vs one-time ingest
- Larger storage footprint

**V2 considerations**: Schema supports planned features without migration:
- Video-level drill-down: Already have videos table with full info
- Channel grouping: Can add groups table with FK to channels
- Incremental updates: views.timestamp enables duplicate detection
