#!/usr/bin/env bash
# Preview your YouTube watch history data with the web interface
# Creates temporary database, runs Flask app in debug mode, then cleans up
# Usage: ./scripts/preview_data.sh <path-to-json-file>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-json-file>"
    echo "Example: $0 ~/Downloads/watch-history.json"
    exit 1
fi

JSON_FILE="$1"
TEMP_DB="preview_temp.db"
PORT=8000

# Cleanup function to run on exit
cleanup() {
    echo ""
    echo "Shutting down and cleaning up..."
    if [ -f "$TEMP_DB" ]; then
        rm -f "$TEMP_DB"
        echo "Removed temporary database: $TEMP_DB"
    fi
    echo "Done."
}

# Register cleanup on script exit (normal or Ctrl+C)
trap cleanup EXIT INT TERM

# Check if JSON file exists
if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file not found: $JSON_FILE"
    exit 1
fi

# Ingest data into temporary database
echo "Creating temporary database and ingesting data..."
echo "Source: $JSON_FILE"
echo "Database: $TEMP_DB"
echo ""

python -c "from src.ingest.pipeline import ingest_json_file; ingest_json_file('$TEMP_DB', '$JSON_FILE')"

echo ""
echo "=========================================="
echo "Starting Flask web server..."
echo "URL: http://127.0.0.1:$PORT"
echo "Press Ctrl+C to stop the server and clean up"
echo "=========================================="
echo ""

# Run Flask app with debug and verbose flags
python -m src.api.app --db "$TEMP_DB" --port "$PORT" --debug --verbose
