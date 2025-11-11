#!/usr/bin/env bash
# Quick test script for ingesting YouTube history data
# Usage: ./scripts/test_ingest.sh <path-to-json-file>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-json-file>"
    echo "Example: $0 ~/Projects/yt-history-data/data/watch-history.json"
    exit 1
fi

JSON_FILE="$1"
DB_FILE="test_ingest.db"

echo "Ingesting $JSON_FILE into $DB_FILE..."
echo ""

# Run ingest
python -c "from src.ingest.pipeline import ingest_json_file; ingest_json_file('$DB_FILE', '$JSON_FILE')"

echo ""
echo "Ingest complete. Database created at: $DB_FILE"
echo "Cleaning up (removing $DB_FILE)..."
rm -f "$DB_FILE"
echo "Done."
