# Operator Requirements

## Overview
Operator persona manages deployment, data ingestion, system lifecycle, and maintenance. Focus on resilience to environment changes (system updates, Python version drift) and ease of management for self-hosted deployment.

## V1 - Core Operations

### Data Ingestion
- Full dataset ingest from YouTube export JSON
- Filter out non-video content during ingest (e.g., YouTube post views)
- Re-ingest entire dataset on demand (acceptable for schema changes in V1)
- Drop database and re-ingest with confirmation prompt for safety
- Source data assumed to be chronologically sorted

### Deployment Management
- Deploy script to set up folder structure if not present
- Place server code in correct location
- Install wrapper command to `~/bin` for easy invocation
- Per-instance deployments in `~/projectDeployments/<instance_name>/`
- Default instance name is "default"
- All operator scripts support `-h` flag for help (prints help only, no side effects)

### Dependency Management
- Loose dependency pinning for Python library versions (e.g., `flask>=2.0,<4.0`)
- Tolerates Python version drift within reason (e.g., Python 3.9-3.12)
- Dependency validation script: verify environment without standing up system
- Per-instance Python virtual environments
- Automatic venv setup and dependency download via script

### Server Lifecycle
- Start script with standard parameters
- Server prints all parameters on startup
- Sane defaults for all parameters, overridable via CLI flags
- Stop script to gracefully shut down server
- Teardown script to clean up deployment (preserves database)
- Single wrapper script with `--instance=<name>` flag (defaults to "default")

### Logging
- Application logs written to file
- Size-based log rotation (1MiB maximum file size)
- Logs located in `~/projectDeployments/<instance>/logs/`
- Log viewing: manual (open file in editor)

### Deployment Structure

**In repository**:
```
/
├── src/              # Source code
├── tests/            # Test suite
├── scripts/          # Operator scripts (deploy.sh, validate.sh, start.sh, stop.sh, teardown.sh)
├── docs/             # Documentation
└── config/           # Configuration templates
```

**At runtime** (outside repo):
```
~/projectDeployments/<instance_name>/
├── data/
│   ├── raw/          # Source JSON files
│   └── db/           # SQLite database
├── logs/             # Application logs (rotated)
├── config/           # Instance-specific configuration
└── venv/             # Python virtual environment
```

## V2 - Advanced Operations

### Incremental Data Updates
- Incremental dataset updates (avoid full re-ingest)
- Detect duplicate records by timestamp
- Stop processing when duplicates encountered (assumes chronological ordering in source)
- Do not update existing records (preserve state like video availability at time of first ingest)

### API Key Management
- Store YouTube API key in instance-specific config
- Secure storage location: `~/projectDeployments/<instance>/config/`

### Parallel Instance Support
- Fully sharded instances: separate database, deploy path, port, server process
- Support arbitrary instance names
- Enable running system for multiple users/datasets simultaneously
- Example use cases:
  - Test instance alongside production
  - Friend's dataset analysis without mixing data

### Error Handling
- API failures emit errors but do not crash backend
- Graceful degradation when API unavailable
- Database inaccessibility should fail fast with clear assertion

## Deferred Decisions
- Per-instance venv necessity (evaluate based on disk usage)
- Whether to support shared venv across instances

## Explicit Non-Requirements
- Automatic backup/restore (can always re-ingest from source)
- Runtime health checks beyond basic dependency validation
- Data validation on ingest (e.g., record count expectations)
- Embedded assumptions about dataset size or structure
- Cleanup/uninstall script (manual removal acceptable)

## Design Constraints
- Must be simple to set up on different systems
- Avoid Node.js-style dependency complexity
- Clear diagnostic output when things break
- Fail fast in development, clear errors in production
