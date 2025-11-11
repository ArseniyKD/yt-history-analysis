# Implementation Plan: V1 End User Features - Iteration 1

**Date**: 2025-11-11
**Session**: v1-end-user-iteration1
**Phase**: Plan
**Scope**: Dataset overview + Top channels with configurable display

## Overview

Building first user-facing feature using blended approach: analytics layer → API layer → frontend layer, fully tested at each stage. After this iteration, the application should be usable end-to-end by an operator.

**Key Validation Goals**:
- ✅ Analytics query patterns (aggregation, grouping)
- ✅ Flask routing and request handling
- ✅ Jinja template rendering
- ✅ End-to-end flow: database → query → API → template → browser
- ✅ Performance with 53k production dataset
- ✅ Complete operator workflow (JSON → DB → web UI)

## Task Breakdown

### Phase 1: Test Infrastructure

#### Task 1: Test Fixture Generator Script
**File**: `tests/fixtures/generate_analytics_sample.py`

**Functionality**:
- Runnable as: `python -m tests.fixtures.generate_analytics_sample`
- Output: `tests/fixtures/analytics_sample.json`
- Target size: ~100-150 records

**Data Generation Requirements**:
- **30 channels** with varying view counts (rationale: test all dropdown options 10, 20, 50, 100)
- View count distribution:
  - 5 channels with 1-2 views (low activity)
  - 10 channels with 3-8 views (medium activity)
  - 10 channels with 9-15 views (high activity)
  - 5 channels with 16-25 views (very high activity)
- Multiple videos per channel: 2-5 videos each
- Rewatches: 20-30% of records are repeat views of same video_id
- Time span: 2020-01-01 to 2024-12-31 (5 years)
- Edge cases:
  - 1 channel with only single view
  - 5-10 records with sentinel channel (deleted videos)
  - At least one video with 5+ rewatches

**Output Format**: Match existing `data_sample.json` structure
```json
{
  "title": "Watched Video Title",
  "titleUrl": "https://www.youtube.com/watch?v=VIDEO_ID",
  "time": "2023-05-15T14:30:00Z"
}
```

**Validation**: Generated file must load successfully via existing `ingest_json_file()`

---

#### Task 2: Generate Test Fixture
**File**: `tests/fixtures/analytics_sample.json` (output)

Run generator script and commit output to repository.

**Verification**:
- File is valid JSON
- Contains expected number of records (~100-150)
- Inspect manually: verify channel distribution, rewatches, deleted videos present

---

### Phase 2: Analytics Layer

#### Task 3: Dataset Overview Query
**File**: `src/analytics/queries.py`

```python
def get_dataset_overview(db_conn: sqlite3.Connection) -> dict:
    """
    Get high-level dataset statistics.

    ALWAYS includes all records (including deleted videos) - this is the
    ground truth of what's in the dataset.

    Args:
        db_conn: SQLite database connection

    Returns:
        dict with keys:
            - first_view: str (YYYY-MM-DD format)
            - last_view: str (YYYY-MM-DD format)
            - total_views: int
            - unique_videos: int
            - unique_channels: int

    Returns None values if database is empty.
    """
```

**SQL Query**:
```sql
SELECT
    MIN(timestamp) as first_view,
    MAX(timestamp) as last_view,
    COUNT(*) as total_views,
    COUNT(DISTINCT video_id) as unique_videos,
    COUNT(DISTINCT channel_id) as unique_channels
FROM views
```

**Implementation Notes**:
- Format dates in Python: `datetime.strptime(...).strftime('%Y-%m-%d')`
- Handle empty database: return dict with None/0 values
- Add logging at DEBUG level: log row count, date range
- Add `breakpoint()` in exception handler

---

#### Task 4: Top Channels Query
**File**: `src/analytics/queries.py`

```python
def get_top_channels(db_conn: sqlite3.Connection,
                     limit: int,
                     include_deleted: bool = False) -> list[dict]:
    """
    Get top N channels ranked by total view count.

    Args:
        db_conn: SQLite database connection
        limit: Maximum number of channels to return (will be bounds-checked by caller)
        include_deleted: If True, include sentinel "Deleted Videos" pseudo-channel.
                        If False, exclude it from results.

    Returns:
        List of dicts, each containing:
            - channel_name: str
            - total_views: int
            - unique_videos: int
            - first_view: str (YYYY-MM format)
            - last_view: str (YYYY-MM format)

        Ordered by total_views DESC, limited to `limit` rows.
    """
```

**SQL Query**:
```sql
SELECT
    c.channel_name,
    COUNT(*) as total_views,
    COUNT(DISTINCT v.video_id) as unique_videos,
    MIN(v.timestamp) as first_view,
    MAX(v.timestamp) as last_view
FROM views v
JOIN channels c ON v.channel_id = c.channel_id
WHERE (c.channel_id != ? OR ? = 1)  -- Exclude deleted if include_deleted=0
GROUP BY c.channel_id, c.channel_name
ORDER BY total_views DESC
LIMIT ?
```

**Implementation Notes**:
- Format dates as `YYYY-MM`: `datetime.strptime(...).strftime('%Y-%m')`
- Parameters: `(DELETED_VIDEO_CHANNEL_ID, int(include_deleted), limit)`
- Return empty list if no results
- Add logging at DEBUG level: log channel count, parameters
- Add `breakpoint()` in exception handler

---

#### Task 5: Logging Infrastructure
**File**: `src/analytics/queries.py`

Add at module level:
```python
import logging

logger = logging.getLogger(__name__)
```

Logging strategy:
- **DEBUG level**: Log function entry with parameters, result counts
- **ERROR level**: Log exceptions before re-raising
- **No INFO/WARNING** for normal operation (keep it quiet)

Example:
```python
def get_top_channels(db_conn, limit, include_deleted=False):
    logger.debug(f"get_top_channels(limit={limit}, include_deleted={include_deleted})")
    try:
        # ... query execution ...
        logger.debug(f"Retrieved {len(results)} channels")
        return results
    except Exception as e:
        logger.error(f"Query failed: {e}")
        breakpoint()  # Only on error
        raise
```

---

### Phase 3: Unit Tests for Analytics

#### Task 6: Unit Tests - Dataset Overview
**File**: `tests/unit/analytics/test_queries.py`

Test cases:

1. **test_dataset_overview_normal**: Load `analytics_sample.json`, verify all aggregates
   - Assert first_view matches earliest timestamp in fixture
   - Assert last_view matches latest timestamp
   - Assert total_views equals record count
   - Assert unique_videos/unique_channels match expected counts

2. **test_dataset_overview_empty_database**: Empty in-memory DB
   - Assert returns dict with None/0 values (no crashes)

3. **test_dataset_overview_includes_deleted**: Verify deleted videos counted
   - Load fixture with known deleted video records
   - Assert total_views includes deleted records
   - Assert unique_channels includes sentinel channel

**Test Setup Pattern**:
```python
import pytest
import sqlite3
from src.db.schema import initialize_database
from src.ingest.pipeline import ingest_json_file
from src.analytics.queries import get_dataset_overview

@pytest.fixture
def analytics_db():
    """In-memory database with analytics_sample.json loaded."""
    conn = sqlite3.connect(':memory:')
    initialize_database(':memory:', conn=conn)
    ingest_json_file('tests/fixtures/analytics_sample.json', ':memory:', conn=conn)
    yield conn
    conn.close()
```

---

#### Task 7: Unit Tests - Top Channels
**File**: `tests/unit/analytics/test_queries.py` (continued)

Test cases:

1. **test_top_channels_ordering**: Verify descending order by view count
   - Get top 10 channels
   - Assert `channels[i].total_views >= channels[i+1].total_views`

2. **test_top_channels_limit_respected**: Test various limits
   - Request limit=5, assert len(results) <= 5
   - Request limit=100, assert len(results) <= 100 (may be fewer channels in fixture)

3. **test_top_channels_exclude_deleted_default**: Default behavior excludes sentinel
   - Get top channels with default params
   - Assert no channel with name matching deleted sentinel

4. **test_top_channels_include_deleted_flag**: Explicit inclusion
   - Get top channels with include_deleted=True
   - If deleted videos exist in fixture, assert sentinel channel present

5. **test_top_channels_aggregates_correct**: Verify per-channel stats
   - Pick one channel with known data in fixture
   - Assert total_views, unique_videos match expected values

6. **test_top_channels_date_format**: Verify YYYY-MM format
   - Assert first_view and last_view match regex `\d{4}-\d{2}`

**Edge Cases**:
- Empty database: returns empty list
- Single channel: returns list with one element
- Limit larger than channel count: returns all channels

---

### Phase 4: API Layer

#### Task 8: Flask Application Setup
**File**: `src/api/app.py`

```python
from flask import Flask, render_template, request
import sqlite3
import logging
from src.analytics import queries

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../frontend/templates')

# Global configuration (set by create_app factory)
DB_PATH = None

def get_db_connection():
    """Get database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
@app.route('/overview', methods=['GET'])
def overview():
    """
    Main overview page showing dataset stats and top channels.

    Query parameters:
        - limit: Number of top channels to show (default: 10, range: 1-1000)
        - include_deleted: 'true' to include deleted videos in top channels (default: false)
    """
    # Parse and validate query parameters
    limit = int(request.args.get('limit', 10))
    limit = max(1, min(limit, 1000))  # Bounds check

    include_deleted_param = request.args.get('include_deleted', 'false').lower()
    include_deleted = include_deleted_param == 'true'

    logger.debug(f"Overview request: limit={limit}, include_deleted={include_deleted}")

    # Execute queries
    conn = get_db_connection()
    try:
        overview_data = queries.get_dataset_overview(conn)
        top_channels = queries.get_top_channels(conn, limit, include_deleted)

        logger.debug(f"Retrieved {len(top_channels)} channels")
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        breakpoint()  # Only on error
        conn.close()
        raise
    finally:
        conn.close()

    return render_template('overview.html',
                          overview=overview_data,
                          channels=top_channels,
                          current_limit=limit,
                          include_deleted=include_deleted)

def create_app(db_path: str, debug: bool = False, verbose: bool = False):
    """
    Factory function to create configured Flask app.

    Args:
        db_path: Path to SQLite database file
        debug: Enable Flask debug mode
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Configured Flask application instance
    """
    global DB_PATH
    DB_PATH = db_path

    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG,
                          format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    elif debug:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    app.config['DEBUG'] = debug

    return app

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='YouTube Watch History Analysis Web Server')
    parser.add_argument('--db', required=True, help='Path to SQLite database')
    parser.add_argument('--port', type=int, default=8000, help='Port number (default: 8000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (Flask debug + breakpoint on errors)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging (SQL queries, request details)')
    args = parser.parse_args()

    application = create_app(args.db, debug=args.debug, verbose=args.verbose)
    application.run(host='127.0.0.1', port=args.port, debug=args.debug)
```

**Key Design Decisions**:
- **GET request**: Filtering view state, not modifying data - GET is semantically correct
- **Query parameters**: Allow bookmarking, browser back/forward works naturally
- **Bounds checking**: `max(1, min(limit, 1000))` prevents absurd values
- **Logging levels**: DEBUG for verbose, WARNING for production
- **Error handling**: `breakpoint()` only on exceptions
- **Factory pattern**: `create_app()` enables testing with different configs

---

### Phase 5: Frontend

#### Task 9: Jinja Template
**File**: `src/frontend/templates/overview.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Watch History - Overview</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            max-width: 1200px;
        }

        h1, h2 {
            color: #333;
        }

        .overview-panel {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }

        .overview-panel ul {
            list-style: none;
            padding: 0;
        }

        .overview-panel li {
            margin: 8px 0;
            font-size: 16px;
        }

        .controls {
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }

        .controls label {
            margin-right: 10px;
            font-weight: bold;
        }

        .controls select {
            padding: 5px;
            font-size: 14px;
        }

        .controls button {
            padding: 6px 15px;
            font-size: 14px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }

        .controls button:hover {
            background-color: #0056b3;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }

        th {
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background-color: #f9f9f9;
        }

        tr:hover {
            background-color: #f0f0f0;
        }

        .rank-column {
            text-align: center;
            font-weight: bold;
        }

        .number-column {
            text-align: right;
        }
    </style>
</head>
<body>
    <h1>YouTube Watch History Overview</h1>

    <div class="overview-panel">
        <h2>Dataset Summary</h2>
        {% if overview and overview.total_views > 0 %}
        <ul>
            <li><strong>Time Span:</strong> {{ overview.first_view }} to {{ overview.last_view }}</li>
            <li><strong>Total Views:</strong> {{ overview.total_views }}</li>
            <li><strong>Unique Videos:</strong> {{ overview.unique_videos }}</li>
            <li><strong>Unique Channels:</strong> {{ overview.unique_channels }}</li>
        </ul>
        {% else %}
        <p>No data available in database.</p>
        {% endif %}
    </div>

    <h2>Top Channels</h2>

    <div class="controls">
        <form method="GET" action="/overview">
            <label for="limit">Show top:</label>
            <select name="limit" id="limit">
                <option value="10" {% if current_limit == 10 %}selected{% endif %}>10</option>
                <option value="20" {% if current_limit == 20 %}selected{% endif %}>20</option>
                <option value="50" {% if current_limit == 50 %}selected{% endif %}>50</option>
                <option value="100" {% if current_limit == 100 %}selected{% endif %}>100</option>
            </select>

            <label for="include_deleted" style="margin-left: 20px;">
                <input type="checkbox" name="include_deleted" id="include_deleted"
                       value="true" {% if include_deleted %}checked{% endif %}>
                Include deleted videos
            </label>

            <button type="submit">Update</button>
        </form>
    </div>

    {% if channels %}
    <table>
        <thead>
            <tr>
                <th class="rank-column">Rank</th>
                <th>Channel Name</th>
                <th class="number-column">Total Views</th>
                <th class="number-column">Unique Videos</th>
                <th>First View</th>
                <th>Last View</th>
            </tr>
        </thead>
        <tbody>
            {% for channel in channels %}
            <tr>
                <td class="rank-column">{{ loop.index }}</td>
                <td>{{ channel.channel_name }}</td>
                <td class="number-column">{{ channel.total_views }}</td>
                <td class="number-column">{{ channel.unique_videos }}</td>
                <td>{{ channel.first_view }}</td>
                <td>{{ channel.last_view }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No channels to display.</p>
    {% endif %}
</body>
</html>
```

**Key Design Decisions**:
- **GET form**: Semantically correct, allows bookmarking
- **Checkbox for deleted videos**: Binary toggle, value='true' when checked
- **Selected state preservation**: Dropdown and checkbox reflect current query params
- **Empty state handling**: Graceful messages when no data
- **Minimal CSS**: Inline styles, no external dependencies, clean table layout
- **Responsive**: Basic viewport meta tag for mobile friendliness

---

### Phase 6: Integration Tests

#### Task 10: Flask Endpoint Tests
**File**: `tests/integration/api/test_endpoints.py`

```python
import pytest
from src.api.app import create_app
from src.db.schema import initialize_database
from src.ingest.pipeline import ingest_json_file

@pytest.fixture
def test_app():
    """Flask test client with analytics_sample.json loaded."""
    # Create temporary database
    db_path = ':memory:'
    initialize_database(db_path)
    ingest_json_file('tests/fixtures/analytics_sample.json', db_path)

    # Create app
    app = create_app(db_path, debug=False, verbose=False)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client
```

Test cases:

1. **test_overview_default_parameters**: GET /overview with no params
   - Assert HTTP 200
   - Assert HTML contains "Dataset Summary"
   - Assert table has <= 10 rows (default limit)
   - Assert no deleted videos in results (default behavior)

2. **test_overview_custom_limit**: GET /overview?limit=20
   - Assert HTTP 200
   - Assert table has <= 20 rows
   - Assert dropdown shows 20 as selected

3. **test_overview_include_deleted**: GET /overview?include_deleted=true
   - Assert HTTP 200
   - Assert checkbox is checked in HTML
   - If deleted videos exist in fixture, verify "Deleted Video" appears in results

4. **test_overview_limit_bounds_checking**: GET /overview?limit=5000
   - Assert HTTP 200 (no crash)
   - Assert effective limit capped at 1000 (or fewer if not enough channels)

5. **test_root_path**: GET /
   - Assert HTTP 200
   - Assert renders same content as /overview

6. **test_overview_empty_database**: Create app with empty database
   - Assert HTTP 200
   - Assert "No data available" message present

7. **test_overview_form_preserves_state**: GET /overview?limit=50&include_deleted=true
   - Assert dropdown shows 50 selected
   - Assert checkbox is checked
   - Verify state persists in rendered form

---

### Phase 7: Database Setup Script

#### Task 11: Setup Script
**File**: `scripts/setup_database.py`

```python
#!/usr/bin/env python3
"""
Setup script to create SQLite database from YouTube watch history JSON.

Usage:
    python scripts/setup_database.py --input data/watch-history.json --output data/youtube_history.db

    Optional flags:
        --force: Overwrite existing database
        --verbose: Show detailed progress
"""

import argparse
import sys
from pathlib import Path

from src.db.schema import initialize_database
from src.ingest.pipeline import ingest_json_file


def main():
    parser = argparse.ArgumentParser(
        description="Initialize SQLite database from YouTube watch history JSON"
    )
    parser.add_argument('--input', required=True,
                       help='Path to YouTube watch-history.json file')
    parser.add_argument('--output', required=True,
                       help='Path to output SQLite database file')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing database if present')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validation
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_file():
        print(f"Error: Input path is not a file: {input_path}", file=sys.stderr)
        sys.exit(1)

    if output_path.exists() and not args.force:
        print(f"Error: Output file already exists: {output_path}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database
    if args.verbose:
        print(f"Creating database schema at {output_path}")

    try:
        initialize_database(str(output_path))
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        if args.verbose:
            raise
        sys.exit(1)

    # Ingest data
    if args.verbose:
        print(f"Ingesting data from {input_path}")
        print("This may take a moment for large files...")

    try:
        stats = ingest_json_file(str(input_path), str(output_path))

        # Success message
        print(f"\n✓ Success!")
        print(f"  Total records processed: {stats['total_records']}")
        print(f"  Videos ingested: {stats['videos']}")
        print(f"  Posts skipped: {stats['posts']}")
        print(f"  Database created: {output_path}")
        print(f"\nTo start the web server, run:")
        print(f"  python -m src.api.app --db {output_path}")

    except Exception as e:
        print(f"\nError during data ingestion: {e}", file=sys.stderr)
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
```

**Key Features**:
- Input validation (file exists, is file not directory)
- Output validation (prevent accidental overwrites without --force)
- Creates output directory if needed
- Reports ingestion statistics
- Helpful error messages
- Shows next step (how to run server)

**Testing**: Manual verification
```bash
# Test with fixture
python scripts/setup_database.py \
    --input tests/fixtures/analytics_sample.json \
    --output /tmp/test.db \
    --verbose

# Verify database created
sqlite3 /tmp/test.db "SELECT COUNT(*) FROM views;"
```

---

### Phase 8: Verification and Quality

#### Task 12: Run All Tests
```bash
pytest tests/ -v
```

**Expected outcomes**:
- All existing tests pass (35 tests from V1 foundation)
- New unit tests pass (~8 new tests for analytics queries)
- New integration tests pass (~7 new tests for API endpoints)
- Total: ~50 tests passing
- Execution time: <2 seconds (in-memory SQLite is fast)

#### Task 13: Manual Verification
**Test with production dataset (53k records)**:

```bash
# Setup database from real data
python scripts/setup_database.py \
    --input ~/data/youtube-watch-history.json \
    --output /tmp/youtube_prod.db \
    --verbose

# Start server
python -m src.api.app --db /tmp/youtube_prod.db --verbose
```

**Manual test checklist**:
1. Navigate to http://localhost:8000
2. Verify dataset overview displays correctly
3. Verify top 10 channels display by default
4. Change dropdown to 20, 50, 100 - verify updates
5. Check "Include deleted videos" - verify results change
6. Verify page loads in <1 second
7. Test browser back/forward buttons (should work due to GET)
8. Copy URL, open in new tab (should preserve state)

**Performance check**:
- Page load time should be <1s for 53k dataset
- If slower, note for potential optimization in Iteration 4

#### Task 14: Code Quality
```bash
# Format with Black
black src/ tests/ scripts/

# Visual inspection
# - All functions have docstrings
# - No TODO comments left in code
# - Logging levels appropriate
# - Error handling present
# - Clear separation of concerns
```

---

## Dependency Updates

**File**: `requirements.txt`

Add:
```
Flask==3.0.0
```

Existing dependencies already cover testing (pytest).

---

## Directory Structure (Post-Implementation)

```
yt-history-analysis/
├── src/
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── queries.py          # NEW: Query functions
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py               # NEW: Flask application
│   ├── db/
│   │   └── schema.py
│   ├── frontend/
│   │   └── templates/
│   │       └── overview.html    # NEW: Main page template
│   ├── ingest/
│   │   ├── parsers.py
│   │   └── pipeline.py
│   └── constants.py
├── tests/
│   ├── fixtures/
│   │   ├── analytics_sample.json      # NEW: Generated fixture
│   │   ├── data_sample.json
│   │   └── generate_analytics_sample.py  # NEW: Generator script
│   ├── integration/
│   │   └── api/
│   │       └── test_endpoints.py      # NEW: API tests
│   └── unit/
│       ├── analytics/
│       │   └── test_queries.py        # NEW: Query tests
│       ├── db/
│       └── ingest/
├── scripts/
│   └── setup_database.py              # NEW: Database setup script
├── requirements.txt                    # MODIFIED: Add Flask
└── docs/
    └── development-trace/
        └── 2025-11-11-v1-end-user-iteration1/
            ├── 01-analysis.md
            └── 02-plan.md              # This file
```

---

## Commit Strategy

**Branch**: `feature/iteration1-overview-ui`

**Commit sequence** (trunk-based workflow):

1. **Test infrastructure**: Generator script + fixture
   ```
   Add analytics test fixture generator with 30-channel dataset

   - tests/fixtures/generate_analytics_sample.py: Script to generate synthetic data
   - tests/fixtures/analytics_sample.json: Generated fixture (100-150 records)
   - Covers edge cases: rewatches, deleted videos, varying activity levels
   ```

2. **Analytics layer**: Query functions + unit tests
   ```
   Implement analytics query layer with unit tests

   - src/analytics/queries.py: get_dataset_overview, get_top_channels
   - tests/unit/analytics/test_queries.py: 8 unit tests
   - Dataset overview always includes deleted videos (ground truth)
   - Top channels has configurable deleted video inclusion
   - Dates formatted in Python (YYYY-MM-DD for overview, YYYY-MM for channels)
   ```

3. **API layer**: Flask app + integration tests
   ```
   Add Flask web server with overview endpoint

   - src/api/app.py: Flask application with /overview route
   - tests/integration/api/test_endpoints.py: 7 integration tests
   - GET-based filtering (bookmarkable URLs)
   - Logging infrastructure with debug/verbose modes
   - Error handling with breakpoint() on exceptions
   ```

4. **Frontend**: Jinja template
   ```
   Add overview page template with configurable display

   - src/frontend/templates/overview.html: Main UI page
   - Dataset summary panel
   - Top channels table with dropdown limit selector
   - Checkbox to include/exclude deleted videos
   - Minimal inline CSS, no external dependencies
   ```

5. **Database setup script**: Operator tooling
   ```
   Add database setup script for end-to-end workflow

   - scripts/setup_database.py: CLI script for JSON → SQLite
   - Input validation and helpful error messages
   - Operator can now: ingest data → start server → view in browser
   - Update requirements.txt: Add Flask==3.0.0
   ```

**PR Title**: "Iteration 1: Dataset overview and top channels UI"

**PR Description**: See PR template below.

---

## Pull Request Description Template

```markdown
## Overview

First iteration of V1 end-user features: dataset overview statistics and configurable top channels display.

**User workflow after this PR**:
1. Ingest data: `python scripts/setup_database.py --input data.json --output db.sqlite`
2. Start server: `python -m src.api.app --db db.sqlite`
3. View in browser: http://localhost:8000

## Changes

### New Features
- **Dataset overview panel**: Time span, total views, unique videos/channels
- **Top channels table**: Ranked by view count, configurable limit (10/20/50/100)
- **Deleted video toggle**: Option to include/exclude deleted videos from top channels
- **Database setup script**: End-to-end operator workflow (JSON → DB → web UI)

### Implementation Details
- **Analytics layer** (`src/analytics/queries.py`): Pure query functions, return formatted data
- **API layer** (`src/api/app.py`): Flask application with GET-based filtering
- **Frontend** (`src/frontend/templates/overview.html`): Server-rendered HTML with minimal CSS
- **Testing**: 15 new tests (8 unit, 7 integration), all passing
- **Logging**: DEBUG/INFO/WARNING levels, `--verbose` flag for detailed output

### Design Decisions
- **GET requests**: Filtering views, not modifying state → allows bookmarks, browser history
- **Date formatting in Python**: Removes Jinja template complexity
- **Dataset overview always includes deleted**: Ground truth of dataset contents
- **Top channels toggle for deleted**: Analysis view where filtering makes sense

## Testing

**Unit tests** (`tests/unit/analytics/test_queries.py`):
- Query correctness with synthetic fixture (30 channels, 100-150 records)
- Edge cases: empty DB, deleted video inclusion/exclusion, limits

**Integration tests** (`tests/integration/api/test_endpoints.py`):
- Flask endpoint behavior, form handling, state preservation
- HTML rendering, empty state handling

**Manual verification** (53k production dataset):
- Page load performance: <1s
- All UI interactions working correctly
- Data accuracy spot-checked

## Files Changed

**New files**:
- `src/analytics/queries.py` (77 lines)
- `src/api/app.py` (125 lines)
- `src/frontend/templates/overview.html` (135 lines)
- `tests/unit/analytics/test_queries.py` (180 lines)
- `tests/integration/api/test_endpoints.py` (140 lines)
- `tests/fixtures/generate_analytics_sample.py` (110 lines)
- `tests/fixtures/analytics_sample.json` (generated, ~4000 lines)
- `scripts/setup_database.py` (90 lines)

**Modified files**:
- `requirements.txt` (+1 line: Flask==3.0.0)

**Total**: ~900 lines of production code, ~320 lines of test code

## Next Steps (Future Iterations)

- **Iteration 2**: Per-year statistics, navigation, rewatch calculations
- **Iteration 3**: Monthly temporal analysis, D3.js visualizations
- **Iteration 4**: Performance optimization, UI polish

## Review Focus Areas

1. **Query design**: Are the SQL patterns appropriate? Performance concerns?
2. **Flask patterns**: Any web development anti-patterns for a newbie to watch out for?
3. **Test coverage**: Are edge cases adequately covered?
4. **UI/UX**: Is the interface clear and functional?
5. **Operator experience**: Is the setup script intuitive?
```

---

## Success Criteria

Iteration 1 is complete when:

1. ✅ **All tests pass**
   - 35 existing tests still passing
   - 8 new unit tests for analytics queries
   - 7 new integration tests for Flask endpoints
   - Total: ~50 tests, <2s execution time

2. ✅ **End-to-end workflow functional**
   - Operator can run `setup_database.py` to create DB from JSON
   - Server starts with `python -m src.api.app --db <path>`
   - UI displays correct data from database

3. ✅ **Feature completeness**
   - Dataset overview shows: time span, total views, unique videos/channels
   - Top channels ranked correctly with configurable limit
   - Deleted video toggle works correctly
   - Form interactions update display as expected

4. ✅ **Performance validated**
   - Page loads in <1s with 53k production dataset
   - No noticeable lag during UI interactions

5. ✅ **Code quality**
   - Black formatting applied
   - All functions have docstrings
   - Logging infrastructure present
   - Error handling with `breakpoint()` on errors
   - No TODO comments or temporary code

6. ✅ **Documentation**
   - README.md updated with server usage instructions (if needed)
   - PR description provides complete context for reviewers

---

## Risk Mitigation

### Risk: Query Performance
- **Mitigation**: Existing indexes on `(channel_id, timestamp)` support GROUP BY and MIN/MAX
- **Validation**: Manual test with 53k dataset in Task 13
- **Fallback**: Defer optimization to Iteration 4 if adequate performance

### Risk: Flask Unfamiliarity
- **Mitigation**: Keep Flask usage simple, leverage factory pattern for testing
- **Learning opportunity**: PR review will provide education on web patterns

### Risk: Test Fixture Inadequacy
- **Mitigation**: 30 channels with 100-150 records covers all dropdown options
- **Flexibility**: Generator script can be re-run if additional edge cases needed

---

## Notes for Execution Phase

- Follow task order strictly: test infra → analytics → API → frontend
- Mark tasks complete immediately after finishing (no batching)
- Run tests after each phase to catch issues early
- Use `--verbose` flag during development for detailed logging
- Keep commits small and focused (one logical change per commit)
- Main branch must pass all tests before merging

---

## Timeline Estimate

**Phase 1-2** (Test infra + Analytics): ~30-40 minutes
**Phase 3-4** (API + Frontend): ~40-50 minutes
**Phase 5-6** (Tests + Script): ~30-40 minutes
**Phase 7-8** (Verification + Quality): ~20-30 minutes

**Total**: ~2-3 hours of focused implementation time

This estimate assumes no major debugging required. Actual time may vary based on issues encountered.
