# Analysis: V1 Setup and Schema Design

**Date**: 2025-11-11
**Session Goal**: Set up development environment and design database schema for YouTube history analysis V1

## Context Review

### Requirements Documents
Reviewed all three persona requirements:
- **End User**: Channel-centric analytics, temporal analysis, top channels, simple UI
- **Operator**: Data ingestion, deployment management, logging, instance isolation
- **Developer**: Testing infrastructure, code organization, debug modes

### Existing Project State
- Project structure already in place: `src/`, `tests/`, `docs/`, `scripts/`, `config/`
- Test organization matches developer requirements (unit/integration/e2e split)
- Comprehensive `.gitignore` already configured
- Test data available at `~/Projects/yt-history-data/data/data_sample.json`

### Environment Discovery
- **Python Version**: 3.13.7 (both `python` and `python3`)
- **Target Compatibility**: Python 3.9+ per operator requirements
- **Platform**: Linux (Arch), local deployment only

## Test Data Analysis

Sample data (`data_sample.json`) observations:
1. **Schema**: Array of objects with `title`, `titleUrl`, `subtitles` (channel info), `time`, `products`, `activityControls`
2. **Non-video content**: Records with "Viewed" prefix are YouTube posts (need filtering)
3. **Deleted/private videos**: Some records lack `subtitles` field (no channel info)
4. **Coverage**: Multiple years (2017-2025), repeat channels, various edge cases

## Database Schema Design

### Design Evolution

**Initial Consideration: Option A (Normalized)**
```
channels: (channel_id, channel_name, channel_url)
videos: (video_id, title, video_url, channel_id [nullable])
views: (view_id, video_id, timestamp)
```

**Initial Consideration: Option B (Denormalized)**
```
channels: (channel_id, channel_name, channel_url)
videos: (video_id, title, video_url, channel_id [nullable], view_count, first_view, last_view)
```

### Key Design Decisions

#### 1. Table Structure: Option A with Modifications
- Chose Option A (normalized views table) for temporal granularity
- Preserves all view timestamps for future analysis
- Enables video-level drill-down without migration (V2 feature)

#### 2. Sentinel Value Instead of Nulls
- **Decision**: Use `'NO_CHANNEL'` sentinel for deleted/private videos
- **Rationale**: Avoids null handling throughout codebase (systems pattern: -1 for invalid)
- **Benefit**: Can query delisted content easily: `WHERE channel_id = 'NO_CHANNEL'`

#### 3. Denormalize channel_id in Views Table
- **Decision**: Add `channel_id` to views table (redundant with videos.channel_id)
- **Rationale**: V1 queries are channel-centric, avoid JOIN overhead
- **Trade-off**: Redundant data vs query performance
- **Assessment**: Read-optimized for analytics, immutable data (no update anomalies)

#### 4. Remove URL Columns
- **Decision**: Store only IDs, compute URLs on demand
- **Rationale**: IDs are stable, URLs are presentation layer
- **Benefit**: Immune to YouTube URL format changes, smaller DB size

### Final Schema

```
channels:
  - channel_id (TEXT PRIMARY KEY)     # Extracted from YouTube URL
  - channel_name (TEXT NOT NULL)
  # Sentinel row: ('NO_CHANNEL', 'Deleted/Private Videos')

videos:
  - video_id (TEXT PRIMARY KEY)       # Extracted from YouTube URL
  - title (TEXT NOT NULL)             # Cleaned (strip "Watched"/"Viewed" prefix)
  - channel_id (TEXT NOT NULL, FK to channels)

views:
  - view_id (INTEGER PRIMARY KEY AUTOINCREMENT)
  - video_id (TEXT NOT NULL, FK to videos)
  - channel_id (TEXT NOT NULL, FK to channels)  # DENORMALIZED for query performance
  - timestamp (TEXT NOT NULL)         # ISO8601 format from source data
  # Index on (channel_id, timestamp) for temporal queries
  # Index on (timestamp) for year/month aggregations
```

### URL Reconstruction (Helper Functions)
```python
def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"

def channel_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}"
```

## Data Processing Requirements

### Record Filtering
- **Video detection**: Check if `titleUrl` contains `/watch?v=` (not title prefix)
- **Post filtering**: Exclude records with `/post/` in URL
- **Rationale**: URL structure more stable than UI text

### Title Cleaning
- Strip action prefixes: "Watched " and "Viewed "
- Store clean titles in DB (actual content titles, not action metadata)

### ID Extraction
- Parse video ID from `titleUrl`: `https://www.youtube.com/watch?v=<video_id>`
- Parse channel ID from `subtitles[0].url`: `https://www.youtube.com/channel/<channel_id>`
- Handle missing `subtitles`: use `'NO_CHANNEL'` sentinel

## Dependencies Identified

### V1 Core Dependencies
```
flask>=2.0,<4.0          # Web framework (chosen over FastAPI for simplicity)
jinja2>=3.0,<4.0         # Template engine (may be bundled with Flask)
pytest>=7.0,<9.0         # Testing framework
black>=22.0,<25.0        # Code formatting
```

### Deferred to V2
- `pytest-cov` for coverage analysis (add when complexity grows)

### Standard Library (No Install Required)
- `sqlite3` - database
- `logging.handlers.RotatingFileHandler` - log rotation

## Setup Tasks Identified

1. Create Python virtual environment in project root
2. Write `requirements.txt` with loose version pinning
3. Create `pyproject.toml` for pytest config and project metadata
4. Install dependencies into venv
5. Copy test data to `tests/fixtures/data_sample.json`
6. Create ADR template in `docs/architecture/`
7. Document schema design as ADR-001

## Open Questions (Resolved)

- ✅ Flask vs FastAPI: Flask chosen (simpler for server-rendered templates)
- ✅ Implementation order: Start with data pipeline, then add web layer
- ✅ Pytest config: Use `pyproject.toml` (modern standard, learning opportunity)
- ✅ Test data location: `tests/fixtures/data_sample.json`
- ✅ ADR template: Create now (document schema decisions)

## Next Steps

Proceed to Plan phase with finalized schema design and clear understanding of:
- Table structure and relationships
- Data processing requirements
- Development environment setup needs
- Testing strategy
