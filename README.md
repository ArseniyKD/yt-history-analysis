# YouTube Watch History Analysis

A local-only data analysis application for YouTube watch history, inspired by "Spotify Wrapped". Analyzes 8+ years of watch history and provides insights through a web interface.

**Key Features**:
- Self-hosted only, no internet access required
- Privacy-first: your data never leaves your machine
- Channel-centric analytics (top channels, viewing patterns, temporal analysis)
- Easily deployable on your own YouTube history dataset

## Quick Start

### Prerequisites

- Python 3.8+
- Linux (developed on Arch, should work on other distributions)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd yt-history-analysis
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv/bin/activate.fish for fish shell
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Verify installation**:
   ```bash
   pytest tests/ -v
   ```

   Expected: All tests pass (35+ tests in <0.1 seconds)

## Running Tests

### Full test suite
```bash
pytest tests/ -v
```

### Specific test categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/ingest/test_parsers.py -v
```

## Usage

### Testing the Ingest Pipeline

Test with the provided sample dataset:
```bash
./scripts/test_ingest.sh tests/fixtures/data_sample.json
```

Expected output:
```
Total records: 9
Videos processed: 7
Records skipped: 2 (posts)
Channels inserted: 6
Videos inserted: 7
Views inserted: 7
```

Test with your own YouTube history:
```bash
# Download your YouTube history from Google Takeout first
./scripts/test_ingest.sh ~/path/to/watch-history.json
```

### Getting Your YouTube History

1. Go to [Google Takeout](https://takeout.google.com/)
2. Select "YouTube and YouTube Music" → "history"
3. Download the archive
4. Extract `watch-history.json` from the archive

## Project Status

**Current Version**: V1 (Data Ingestion Pipeline)

**Implemented**:
- ✅ Database schema with denormalized design for analytics
- ✅ YouTube URL parsing (video IDs, channel IDs)
- ✅ JSON ingestion pipeline with transaction handling
- ✅ Comprehensive test suite (unit + integration tests)
- ✅ Verified with 53k record production dataset (1.28s ingest time)

**Planned**:
- 🔲 Analytics queries (top channels, view counts, temporal patterns)
- 🔲 Web interface with D3.js visualizations
- 🔲 Backend server (Flask/FastAPI)
- 🔲 Incremental data updates (V2)
- 🔲 YouTube API enrichment (V2)
- 🔲 Channel grouping (V2)

See `docs/requirements/` for detailed roadmap.

## Project Structure

```
src/
├── constants.py          # Domain constants (sentinel values)
├── db/
│   └── schema.py         # Database schema definition
└── ingest/
    ├── parsers.py        # URL parsing and record parsing
    └── pipeline.py       # Ingestion pipeline with transactions

tests/
├── fixtures/             # Test data (sanitized/synthetic)
├── unit/                 # Unit tests (in-memory SQLite)
└── integration/          # Integration tests (full pipeline)

docs/
├── requirements/         # Feature requirements by persona
├── architecture/         # Architecture Decision Records (ADRs)
└── development-trace/    # Development session logs

scripts/
└── test_ingest.sh        # Quick test script for manual verification
```

## Development

### Setting Up Development Environment

Follow the Quick Start steps above, then:

```bash
# Verify imports work
python -c "from src.db.schema import init_schema; print('Schema import: OK')"
python -c "from src.ingest.parsers import parse_record; print('Parser import: OK')"
python -c "from src.ingest.pipeline import ingest_json_file; print('Pipeline import: OK')"
```

### Development Workflow

This project uses trunk-based development:
- Main branch always builds and passes all tests
- Short-lived feature branches (1-5 commits)
- GitHub PR process for code review

See `CLAUDE.md` for detailed development philosophy and standards.

### Running Tests During Development

```bash
# Run tests automatically on file changes (requires pytest-watch)
pip install pytest-watch
ptw tests/
```

## Documentation

- `CLAUDE.md`: Development philosophy and coding standards
- `docs/requirements/`: Feature requirements by persona (end user, operator, developer)
- `docs/architecture/`: Architecture Decision Records (ADRs) for design decisions
- `docs/development-trace/`: Session logs documenting implementation process

## Privacy & Data

This application is designed with privacy as a priority:
- All processing happens locally on your machine
- No data is sent to external servers
- No authentication or user tracking
- Your watch history stays on your computer

The repository contains NO real YouTube watch history data - only synthetic/sanitized test fixtures.

## License

[To be determined]

## Contributing

This is currently a personal project. If you're interested in contributing, please open an issue first to discuss proposed changes.
