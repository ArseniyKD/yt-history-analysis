# Plan: V1 Development Environment + Ingest Pipeline

**Date**: 2025-11-11
**Goal**: Set up development environment and implement data ingestion pipeline for V1

## Implementation Order

Following KISS principle and iterative development:
1. **Setup Phase**: Foundation (venv, dependencies, documentation)
2. **Ingest Pipeline**: Core data processing logic
3. **Deferred**: Web interface, operator scripts, analytics queries (next session)

---

## Phase 1: Setup (Foundation)

### 1.1 Virtual Environment + Dependencies

**Create venv**:
```bash
python -m venv venv
source venv/bin/activate  # or venv/bin/activate.fish
```

**Create `requirements.txt`**:
```
# Web framework
flask>=2.0,<4.0
jinja2>=3.0,<4.0

# Testing
pytest>=7.0,<9.0

# Code formatting
black>=22.0,<25.0
```

**Install dependencies**:
```bash
pip install -r requirements.txt
```

**Success Criteria**: `pip list` shows all dependencies installed

---

### 1.2 Project Configuration

**Create `pyproject.toml`**:
- Project metadata (name, version, python_requires>=3.9)
- pytest configuration (testpaths, python_files, python_classes, python_functions)
- Black configuration (default settings acceptable)

**Why pyproject.toml**: Modern Python standard, consolidates config, learning opportunity

**Success Criteria**: `pytest --collect-only` shows test discovery working (even with 0 tests)

---

### 1.3 Test Data Fixture

**Action**: Copy test data
```bash
cp ~/Projects/yt-history-data/data/data_sample.json tests/fixtures/data_sample.json
```

**Purpose**: Committed test data for reproducible testing across systems

**Success Criteria**: File exists and is readable

---

### 1.4 ADR Infrastructure

**Create ADR template**: `docs/architecture/ADR-template.md`
- Standard structure: Title, Status, Context, Decision, Consequences
- Reference for future architectural decisions

**Write ADR-001**: Document schema design decisions
- Rationale for denormalization (channel_id in views)
- Rationale for sentinel value over nulls
- Rationale for storing IDs only (no URLs)
- Rationale for normalized views table (preserve temporal granularity)

**Success Criteria**: ADR-001 captures key schema design trade-offs

---

## Phase 2: Ingest Pipeline Implementation

### 2.1 Database Schema Creation

**File**: `src/db/schema.py`

**Functionality**:
- Define table creation SQL for channels, videos, views
- Create indexes for query optimization:
  - `idx_views_channel_timestamp` on views(channel_id, timestamp)
  - `idx_views_timestamp` on views(timestamp)
- Function to initialize database with schema
- Function to insert sentinel channel (`'NO_CHANNEL'`, `'Deleted/Private Videos'`)

**Design Pattern**: Pure SQL strings, executed via sqlite3 cursor

**Success Criteria**:
- Can call `init_schema(conn)` and create all tables
- Sentinel channel inserted automatically

---

### 2.2 URL Parsing Utilities

**File**: `src/ingest/parsers.py`

**Functions**:

```python
def is_video_record(record: dict) -> bool:
    """
    Filter: only process video records, skip posts.
    Detection: Check if titleUrl contains '/watch?v='
    """

def clean_title(title: str) -> str:
    """
    Remove action prefix from title.
    Strip: 'Watched ' and 'Viewed ' prefixes
    """

def extract_video_id(url: str) -> str:
    """
    Parse video ID from watch URL.
    Extract from: 'https://www.youtube.com/watch?v=<video_id>'
    Handle: Query parameters, different formats
    """

def extract_channel_id(url: str) -> str:
    """
    Parse channel ID from channel URL.
    Extract from: 'https://www.youtube.com/channel/<channel_id>'
    """

def parse_record(record: dict) -> tuple:
    """
    Parse a single YouTube history record.

    Returns: (video_id, title, channel_id, timestamp)
    - video_id: extracted from titleUrl
    - title: cleaned title (prefix stripped)
    - channel_id: extracted from subtitles[0].url, or 'NO_CHANNEL'
    - timestamp: from 'time' field (ISO8601)

    Raises: ValueError if record malformed or not a video
    """
```

**Edge Cases to Handle**:
- Missing `subtitles` field → channel_id = `'NO_CHANNEL'`
- Non-video records (posts) → raise ValueError or return None
- Malformed URLs → raise ValueError with clear message

**Success Criteria**: Unit tests cover all edge cases from test data

---

### 2.3 Ingest Pipeline Logic

**File**: `src/ingest/pipeline.py`

**Main Function**:
```python
def ingest_json_file(db_path: str, json_path: str) -> dict:
    """
    Ingest YouTube history JSON file into SQLite database.

    Process:
    1. Load JSON file
    2. Filter and parse records
    3. Insert into DB (channels → videos → views)
    4. Transaction handling (commit all or rollback)

    Returns: dict with stats (records_processed, records_skipped, etc.)
    """
```

**Implementation Details**:
- Load entire JSON file (acceptable for 58k records)
- Filter out non-video records using `is_video_record()`
- Parse each record using `parse_record()`
- Batch inserts for performance (or use executemany)
- Insert order: channels first, then videos, then views (FK integrity)
- Use `INSERT OR IGNORE` for channels/videos (handle duplicates)
- Transaction wrapper for atomicity

**Error Handling**:
- File not found → clear error message
- JSON parse error → clear error message
- DB constraint violations → rollback and report which record failed
- Use assertions for "should never happen" cases

**Success Criteria**: Can ingest test data and query results

---

### 2.4 Testing

**Test Organization**:

```
tests/
├── fixtures/
│   └── data_sample.json
├── unit/
│   ├── ingest/
│   │   ├── test_parsers.py
│   │   └── test_pipeline.py
│   └── db/
│       └── test_schema.py
└── integration/
    └── test_full_ingest.py
```

**Unit Tests** (`tests/unit/ingest/test_parsers.py`):
- `test_is_video_record()`: video URLs pass, post URLs fail
- `test_clean_title()`: strips "Watched "/"Viewed " prefixes
- `test_extract_video_id()`: handles various URL formats
- `test_extract_channel_id()`: handles channel URLs
- `test_parse_record_normal()`: standard record with channel
- `test_parse_record_no_channel()`: deleted/private video
- `test_parse_record_post()`: raises ValueError for posts

**Unit Tests** (`tests/unit/db/test_schema.py`):
- `test_init_schema()`: creates all tables
- `test_sentinel_channel()`: NO_CHANNEL inserted

**Integration Tests** (`tests/integration/test_full_ingest.py`):
- `test_ingest_sample_data()`: Full pipeline test
  - Ingest `data_sample.json`
  - Query channel count
  - Query video count
  - Query view count
  - Verify specific records exist
  - Verify NO_CHANNEL records exist

**Test Fixtures**:
- In-memory SQLite DB (`:memory:`) for fast tests
- Setup/teardown using pytest fixtures

**Test Runner**:
- Direct `pytest` invocation (no wrapper script needed yet)
- Run from project root: `pytest tests/`

**Success Criteria**: All tests pass, coverage of main code paths

---

## Phase 3: Deferred to Next Session

These are out of scope for this session:
- Web interface (Flask app, templates)
- Operator scripts (deploy, start, stop, ingest CLI)
- Analytics query functions
- Frontend visualizations

---

## Success Criteria Summary

**Setup Phase**:
- ✅ Virtual environment created with dependencies installed
- ✅ `pyproject.toml` configured for pytest
- ✅ Test data copied to `tests/fixtures/`
- ✅ ADR template and ADR-001 written

**Ingest Phase**:
- ✅ Database schema creates all tables with indexes
- ✅ URL parsing handles all edge cases
- ✅ Full ingest pipeline processes test data
- ✅ All unit and integration tests pass
- ✅ Can query basic stats from ingested data

---

## Implementation Notes

**Order of Execution**:
1. Setup tasks (can be done in parallel)
2. Schema implementation → schema tests
3. Parser implementation → parser tests
4. Pipeline implementation → pipeline tests
5. Integration test (validates full flow)

**Testing Philosophy**:
- Write tests alongside implementation (not strict TDD, but close)
- Fast feedback loop: unit tests should run in milliseconds
- Integration tests can be slower (full DB operations)

**Commit Strategy**:
- Commit after each logical unit (setup, schema, parsers, pipeline)
- Keep commits small and focused
- All tests must pass before commit
